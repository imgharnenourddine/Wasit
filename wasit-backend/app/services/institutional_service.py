import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.institution import Class, Filiere, School
from app.models.student import Student
from app.models.user import Role, User
from app.schemas.institution import ClassCreate, FiliereCreate, SchoolCreate
from app.services.chat_service import get_or_create_class_channel


async def create_school(db: AsyncSession, data: SchoolCreate) -> School:
    school = School(name=data.name, domain=data.domain)
    db.add(school)
    await db.commit()
    await db.refresh(school)
    return school


async def get_schools(db: AsyncSession) -> list[School]:
    result = await db.scalars(select(School).order_by(School.created_at.desc()))
    return list(result.all())


async def create_filiere(db: AsyncSession, data: FiliereCreate) -> Filiere:
    school = await db.get(School, data.school_id)
    if not school:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")

    if data.responsible_id:
        user = await db.get(User, data.responsible_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Responsible user not found")

    filiere = Filiere(name=data.name, school_id=data.school_id, responsible_id=data.responsible_id)
    db.add(filiere)
    await db.commit()
    await db.refresh(filiere)
    return filiere


async def create_class(db: AsyncSession, data: ClassCreate) -> Class:
    filiere = await db.get(Filiere, data.filiere_id)
    if not filiere:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filiere not found")

    class_room = Class(name=data.name, filiere_id=data.filiere_id, academic_year=data.academic_year)
    db.add(class_room)
    await db.commit()
    await db.refresh(class_room)
    
    # Provision chat channel
    await get_or_create_class_channel(db, class_room.id)
    
    return class_room


async def assign_delegate(db: AsyncSession, class_id: uuid.UUID, user_id: uuid.UUID) -> Class:
    class_room = await db.get(Class, class_id)
    if not class_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.role != Role.delegate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assigned user must have delegate role",
        )

    class_room.delegate_id = user_id
    await db.commit()
    
    # Sync delegate to chat channel
    await get_or_create_class_channel(db, class_id)
    
    result = await db.scalar(select(Class).where(Class.id == class_id).options(selectinload(Class.delegate)))
    return result


async def get_class_with_details(db: AsyncSession, class_id: uuid.UUID) -> dict:
    result = await db.scalar(
        select(Class)
        .where(Class.id == class_id)
        .options(selectinload(Class.filiere).selectinload(Filiere.school), selectinload(Class.delegate))
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")

    students_count = await db.scalar(select(func.count(Student.id)).where(Student.class_id == class_id))
    return {
        "school": {
            "id": str(result.filiere.school.id),
            "name": result.filiere.school.name,
            "domain": result.filiere.school.domain,
        },
        "filiere": {
            "id": str(result.filiere.id),
            "name": result.filiere.name,
            "responsible_id": str(result.filiere.responsible_id) if result.filiere.responsible_id else None,
        },
        "class": {
            "id": str(result.id),
            "name": result.name,
            "academic_year": result.academic_year,
            "delegate_id": str(result.delegate_id) if result.delegate_id else None,
        },
        "students_count": students_count or 0,
    }
