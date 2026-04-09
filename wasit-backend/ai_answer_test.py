#!/usr/bin/env python3
"""
Test the AI delegate bot RAG answers.
The PDF uploaded in the main integration test contains:
  "Lundi 08:00-10:00 Mathematiques Salle A101 Examen DS1 Jeudi 14:00"

This script:
1. Registers a fresh admin user and logs in
2. Creates school → filière → class
3. Uploads a richer timetable & exam PDF
4. Asks several questions to POST /debug/ai-query
5. Checks answers contain expected content from the PDF
"""

import io, sys, json, random, string, httpx

BASE = "http://localhost:8001/api/v1"

def rnd(k=7):
    return "".join(random.choices(string.ascii_lowercase, k=k))

RESULTS = []

def check(label, passed, got=""):
    mark = "✅ PASS" if passed else "❌ FAIL"
    RESULTS.append({"label": label, "pass": passed})
    print(f"\n  {mark}  {label}")
    if got:
        for line in got.splitlines():
            print(f"          {line}")

def section(t):
    print(f"\n{'━'*62}\n  {t}\n{'━'*62}")

# ── Rich PDF with a real timetable and exam schedule ─────────────────
# Text embedded in page stream (plain ASCII for simplicity)
PAGE_TEXT = (
    "EMPLOI DU TEMPS - GL2 2025-2026\n"
    "Lundi    08:00-10:00  Mathematiques       Salle A101  Pr. Benali\n"
    "Lundi    10:00-12:00  Algorithmique       Salle B202  Pr. Alami\n"
    "Mardi    08:00-10:00  Physique            Salle C303  Pr. Sadiki\n"
    "Mercredi 14:00-16:00  Bases de donnees    Salle A101  Pr. Chakir\n"
    "Jeudi    08:00-10:00  Reseaux             Salle Lab1  Pr. Hamid\n"
    "Vendredi 10:00-12:00  Anglais Technique   Salle D404  Pr. Layla\n"
    "\n"
    "CALENDRIER DES EXAMENS\n"
    "DS1 Mathematiques    Jeudi 24 Avril 2026 08:00  Salle A101\n"
    "DS1 Algorithmique    Vendredi 25 Avril 2026 10:00  Salle B202\n"
    "Partiel Physique     Lundi 28 Avril 2026 14:00  Salle C303\n"
    "DS1 Reseaux          Mardi 29 Avril 2026 08:00  Salle Lab1\n"
)

def make_pdf(text: str) -> bytes:
    """Create a minimal valid PDF with the given text in its page stream."""
    encoded = text.encode("latin-1", errors="replace")
    stream = b"BT /F1 10 Tf 30 750 Td\n"
    # Write each line with a newline move
    for line in text.split("\n"):
        safe = line.encode("latin-1", errors="replace")
        stream += b"(" + safe.replace(b"(", b"\\(").replace(b")", b"\\)") + b") Tj T*\n"
    stream += b"ET"
    length = len(stream)

    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        + f"4 0 obj<</Length {length}>>stream\n".encode()
        + stream
        + b"\nendstream\nendobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Courier>>endobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000266 00000 n \n"
        b"0000000999 00000 n \n"
        b"trailer<</Size 6/Root 1 0 R>>\n"
        b"startxref\n1060\n%%EOF"
    )
    return pdf

client = httpx.Client(timeout=60)
PW = "Test@1234"
email_admin = f"ai_test_{rnd()}@gmail.com"

# ── 1. Setup: register + login ────────────────────────────────────────
section("Setup: register, login, create school→filière→class, upload PDF")

r = client.post(f"{BASE}/auth/register", json={
    "email": email_admin, "password": PW,
    "first_name": "AITest", "last_name": "Admin", "role": "admin"
})
admin_id = r.json().get("id")
r = client.post(f"{BASE}/auth/login", json={"email": email_admin, "password": PW})
token = r.json().get("access_token")
H = {"Authorization": f"Bearer {token}"}

# School
r = client.post(f"{BASE}/schools", json={"name": f"TestSchool {rnd(4)}", "domain": f"{rnd()}.edu"}, headers=H)
school_id = r.json().get("id")

# Filière  (responsible = our admin)
r = client.post(f"{BASE}/filieres", json={"name": f"GL-{rnd(3)}", "school_id": str(school_id), "responsible_id": admin_id}, headers=H)
filiere_id = r.json().get("id")

# Class
r = client.post(f"{BASE}/classes", json={"filiere_id": str(filiere_id), "name": f"GL2-{rnd(3)}", "academic_year": "2025-2026"}, headers=H)
class_id = r.json().get("id")

# Upload rich timetable PDF
pdf_bytes = make_pdf(PAGE_TEXT)
r = client.post(
    f"{BASE}/filieres/{filiere_id}/documents/timetable",
    headers=H,
    files={"file": ("timetable.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
)
extracted = r.json().get("extracted_text", "")
print(f"\n  ℹ  PDF extracted_text:\n")
for line in extracted.splitlines():
    print(f"       {line}")

# Upload exam PDF (same content for test)
r = client.post(
    f"{BASE}/filieres/{filiere_id}/documents/exam_schedule",
    headers=H,
    files={"file": ("exams.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
)
print(f"\n  ✅ Setup complete — class_id: {class_id}")

# ── 2. AI query tests ─────────────────────────────────────────────────
section("AI Delegate RAG Answer Tests  (POST /debug/ai-query)")

def ask(question: str) -> str:
    r = client.post(f"{BASE}/debug/ai-query",
                    json={"class_id": str(class_id), "question": question},
                    headers=H)
    if r.status_code != 200:
        return f"[HTTP {r.status_code}] {r.text[:200]}"
    return r.json().get("answer", "")

# Test 1 — Monday timetable
q = "Quels sont les cours du Lundi ?"
answer = ask(q)
passed = any(k in answer.lower() for k in ["lundi", "math", "algorithmi", "08:00", "a101"])
check(f'Q: "{q}"', passed, f"A: {answer}")

# Test 2 — Specific subject room
q = "Dans quelle salle a lieu le cours de Bases de données ?"
answer = ask(q)
passed = any(k in answer.lower() for k in ["a101", "mercredi", "chakir", "bases"])
check(f'Q: "{q}"', passed, f"A: {answer}")

# Test 3 — Exam schedule general
q = "Quels sont les prochains examens ?"
answer = ask(q)
passed = any(k in answer.lower() for k in ["ds1", "exam", "avril", "math", "algo", "partiel"])
check(f'Q: "{q}"', passed, f"A: {answer}")

# Test 4 — Specific exam
q = "Quand est l'examen de Mathematiques ?"
answer = ask(q)
passed = any(k in answer.lower() for k in ["24 avril", "jeudi", "08:00", "a101", "math"])
check(f'Q: "{q}"', passed, f"A: {answer}")

# Test 5 — Thursday courses
q = "Qu'est-ce qu'on a comme cours le Jeudi ?"
answer = ask(q)
passed = any(k in answer.lower() for k in ["réseau", "reseau", "jeudi", "lab", "hamid"])
check(f'Q: "{q}"', passed, f"A: {answer}")

# Test 6 — Ask about a teacher
q = "Qui enseigne l'Algorithmique ?"
answer = ask(q)
passed = answer is not None and any(k in answer.lower() for k in ["alami", "algorithmi", "prof"])
check(f'Q: "{q}"', passed, f"A: {answer or '(None — bot did not recognize intent)'}")

# Test 7 — Unknown topic (should gracefully say not found)
q = "Quel est le numéro de téléphone du directeur ?"
answer = ask(q)
passed = answer is not None and len(answer) > 5  # bot must reply something
check(f'Q: "{q}" (out-of-context – graceful reply)', passed, f"A: {answer or '(None)'}")

# ── Summary ───────────────────────────────────────────────────────────
total = len(RESULTS)
passed_n = sum(1 for r in RESULTS if r["pass"])
print(f"\n{'═'*62}")
print(f"  AI RAG RESULTS: {passed_n}/{total} passed {'🎉' if passed_n == total else '⚠️'}")
print(f"{'═'*62}\n")
sys.exit(0 if passed_n == total else 1)
