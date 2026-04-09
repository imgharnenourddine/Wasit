"""LangChain-based tool implementations for the AI Delegate bot.

Instead of querying structured DB rows (TimetableSlot, ExamEvent), we now:
  1. Load the extracted PDF text stored in FilierePDFDocument.
  2. Split into chunks with RecursiveCharacterTextSplitter.
  3. Build an ephemeral FAISS vector store using Mistral embeddings.
  4. Retrieve the top-k relevant chunks.
  5. Stuff them into a prompt and call the LLM for a natural-language answer.
"""

from __future__ import annotations

from uuid import UUID

from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_mistralai import ChatMistralAI, MistralAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.delegate_data import FilierePDFDocument
from app.models.institution import Class
from app.models.student import Student
from app.models.user import User
from sqlalchemy import func


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_CHUNK_SIZE = 800
_CHUNK_OVERLAP = 100
_TOP_K = 5

_RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "Tu es le délégué numérique de la classe. Réponds en français de manière concise "
                "en te basant UNIQUEMENT sur les informations contenues dans le contexte suivant. "
                "Si l'information n'est pas présente dans le contexte, dis-le clairement.\n\n"
                "Contexte:\n{context}"
            ),
        ),
        ("human", "{input}"),
    ]
)


def _build_retrieval_chain(text: str):
    """Build an ephemeral LangChain retrieval chain from a plain-text document."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=_CHUNK_SIZE,
        chunk_overlap=_CHUNK_OVERLAP,
    )
    chunks = splitter.create_documents([text])

    embeddings = MistralAIEmbeddings(
        api_key=settings.MISTRAL_API_KEY,
        model="mistral-embed",
    )
    vector_store = FAISS.from_documents(chunks, embeddings)
    retriever = vector_store.as_retriever(search_kwargs={"k": _TOP_K})

    llm = ChatMistralAI(
        api_key=settings.MISTRAL_API_KEY,
        model="mistral-large-latest",
        temperature=0,
    )
    combine_docs_chain = create_stuff_documents_chain(llm, _RAG_PROMPT)
    return create_retrieval_chain(retriever, combine_docs_chain)


async def query_filiere_document(
    db: AsyncSession,
    filiere_id: UUID,
    doc_type: str,
    question: str,
) -> str:
    """Answer a question using RAG over the stored PDF text for a filière.

    Args:
        db: Async SQLAlchemy session.
        filiere_id: The filière whose PDF to query.
        doc_type: ``"timetable"`` or ``"exam_schedule"``.
        question: Natural-language question from the student.

    Returns:
        Natural-language answer, or a polite "not available" message.
    """
    result = await db.execute(
        select(FilierePDFDocument).where(
            FilierePDFDocument.filiere_id == filiere_id,
            FilierePDFDocument.doc_type == doc_type,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        label = "emploi du temps" if doc_type == "timetable" else "calendrier des examens"
        return (
            f"Le {label} de cette filière n'a pas encore été uploadé par le chef de filière. "
            "Contactez-le directement pour obtenir l'information."
        )

    chain = _build_retrieval_chain(doc.extracted_text)
    # LangChain chains are sync; run in the default thread pool
    from asyncio import to_thread
    response = await to_thread(chain.invoke, {"input": question})
    return str(response.get("answer", "Désolé, je n'ai pas pu trouver la réponse."))


# ---------------------------------------------------------------------------
# Trombinoscope / student count helpers (unchanged, still DB-backed)
# ---------------------------------------------------------------------------

async def get_trombinoscope(
    db: AsyncSession, class_id: UUID, name_query: str | None = None, limit: int = 50
) -> list[dict[str, str | None]]:
    stmt = (
        select(Student, User)
        .join(User, Student.user_id == User.id)
        .where(Student.class_id == class_id, Student.is_active.is_(True))
    )
    if name_query:
        q = f"%{name_query.strip()}%"
        stmt = stmt.where(
            (User.first_name.ilike(q))
            | (User.last_name.ilike(q))
            | (func.concat(User.first_name, " ", User.last_name).ilike(q))
        )
    stmt = stmt.limit(limit)
    rows = (await db.execute(stmt)).all()
    return [
        {
            "first_name": u.first_name,
            "last_name": u.last_name,
            "student_number": s.student_number,
            "photo_url": s.photo_url,
        }
        for s, u in rows
    ]


async def get_class_student_count(db: AsyncSession, class_id: UUID) -> int:
    n = await db.scalar(select(func.count(Student.id)).where(Student.class_id == class_id))
    return int(n or 0)


# ---------------------------------------------------------------------------
# Resolve filiere_id from class_id (needed by autonomous_reply_from_tools)
# ---------------------------------------------------------------------------

async def _get_filiere_id(db: AsyncSession, class_id: UUID) -> UUID | None:
    c = await db.get(Class, class_id)
    return c.filiere_id if c else None


# ---------------------------------------------------------------------------
# Top-level autonomous reply dispatcher
# ---------------------------------------------------------------------------

async def autonomous_reply_from_tools(
    db: AsyncSession, class_id: UUID, user_text: str
) -> str | None:
    """Return a natural-language answer when the message maps to helper data."""
    t = user_text.lower()

    # --- Exam schedule ---
    if any(k in t for k in ("exam", "examen", "contrôle", "ds", "partiel", "exams")):
        filiere_id = await _get_filiere_id(db, class_id)
        if filiere_id is None:
            return "Impossible d'identifier la filière de cette classe."
        return await query_filiere_document(db, filiere_id, "exam_schedule", user_text)

    # --- Timetable ---
    if any(
        k in t
        for k in (
            "emploi",
            "timetable",
            "schedule",
            "cours",
            "jeudi",
            "lundi",
            "mardi",
            "mercredi",
            "vendredi",
            "salle",
            "horaire",
            "enseigne",
            "professeur",
            " prof",
        )
    ):
        filiere_id = await _get_filiere_id(db, class_id)
        if filiere_id is None:
            return "Impossible d'identifier la filière de cette classe."
        return await query_filiere_document(db, filiere_id, "timetable", user_text)

    # --- Trombinoscope ---
    if any(k in t for k in ("trombi", "étudiant", "student", "élève", "who is", "qui est")):
        parts = user_text.split()
        name_q = parts[-1] if len(parts) > 1 and len(parts[-1]) > 2 else None
        rows = await get_trombinoscope(db, class_id, name_query=name_q)
        if not rows:
            return "Aucun étudiant ne correspond dans le trombinoscope."
        lines = [f"• {r['first_name']} {r['last_name']}" for r in rows[:15]]
        return "Trombinoscope:\n" + "\n".join(lines)

    # --- Student count ---
    if any(k in t for k in ("combien", "how many", "nombre", "effectif", "students in")):
        n = await get_class_student_count(db, class_id)
        return f"Effectif enregistré pour cette classe: {n} étudiant(s)."

    return None
