from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.student import Student
from app.models.ticket import Ticket, TicketHistory, TicketStatus
from app.models.user import User
from app.schemas.tickets import ProblemSubmit, TicketHistoryResponse, TicketResponse, TicketUpdate
from app.services.tickets import (
    create_ticket_from_problem,
    get_all_open_tickets,
    get_class_tickets,
    get_student_tickets,
    get_ticket,
    update_ticket_status,
)

router = APIRouter(prefix="", tags=["tickets"])


async def _get_student_profile(db: AsyncSession, user_id: UUID) -> Student:
    result = await db.execute(select(Student).where(Student.user_id == user_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No student profile linked to current user",
        )
    return student


def _to_response(ticket: Ticket, history: list[TicketHistory] | None = None) -> TicketResponse:
    items = history or []
    return TicketResponse(
        id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        category=ticket.category,
        priority=ticket.priority,
        status=ticket.status,
        assigned_to=ticket.assigned_to,
        student_id=ticket.student_id,
        class_id=ticket.class_id,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        history=[
            TicketHistoryResponse(
                old_status=h.old_status,
                new_status=h.new_status,
                note=h.note,
                changed_by=h.changed_by,
                created_at=h.created_at,
            )
            for h in items
        ],
    )


@router.post("/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: ProblemSubmit,
    class_id: UUID = Query(..., description="Class identifier"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("student")),
) -> TicketResponse:
    student = await _get_student_profile(db, user.id)
    ticket = await create_ticket_from_problem(
        db=db,
        student_id=student.id,
        class_id=class_id,
        raw_text=payload.raw_text,
        changed_by_user_id=user.id,
    )
    _, history = await get_ticket(db, ticket.id)
    return _to_response(ticket, history)


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def read_ticket(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TicketResponse:
    ticket, history = await get_ticket(db, ticket_id)
    staff_roles = {"delegate", "teacher", "admin", "listening"}
    if user.role.value not in staff_roles:
        student = await _get_student_profile(db, user.id)
        if ticket.student_id != student.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to access this ticket")
    return _to_response(ticket, history)


@router.get("/students/me/tickets", response_model=list[TicketResponse])
async def read_my_tickets(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("student")),
) -> list[TicketResponse]:
    student = await _get_student_profile(db, user.id)
    tickets = await get_student_tickets(db, student.id)
    return [_to_response(ticket) for ticket in tickets]


@router.get("/classes/{class_id}/tickets", response_model=list[TicketResponse])
async def read_class_tickets(
    class_id: UUID,
    status_filter: TicketStatus | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("delegate", "teacher", "admin")),
) -> list[TicketResponse]:
    tickets = await get_class_tickets(db, class_id=class_id, status_filter=status_filter)
    return [_to_response(ticket) for ticket in tickets]


@router.patch("/tickets/{ticket_id}/status", response_model=TicketResponse)
async def patch_ticket_status(
    ticket_id: UUID,
    payload: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("delegate", "teacher", "admin", "listening")),
) -> TicketResponse:
    ticket = await update_ticket_status(
        db=db,
        ticket_id=ticket_id,
        new_status=payload.status,
        changed_by_id=user.id,
        note=payload.note,
    )
    _, history = await get_ticket(db, ticket.id)
    return _to_response(ticket, history)


@router.get("/admin/tickets", response_model=list[TicketResponse])
async def read_admin_tickets(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
) -> list[TicketResponse]:
    tickets = await get_all_open_tickets(db)
    return [_to_response(ticket) for ticket in tickets]
