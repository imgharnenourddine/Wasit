import math
import secrets
import string
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.models.auth import Role, User
from app.models.institutional import Class
from app.models.students import ProjectGroup, ProjectGroupMember, Student


def _generate_temp_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def bulk_create_students(db: AsyncSession, class_id: uuid.UUID, parsed_rows: list[dict]) -> dict:
    class_room = await db.get(Class, class_id)
    if not class_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")

    created = 0
    skipped = 0
    errors: list[dict] = []

    for row in parsed_rows:
        existing = await db.scalar(select(User).where(User.email == row["email"]))
        if existing:
            skipped += 1
            errors.append({"email": row["email"], "error": "Email already exists"})
            continue

        temp_password = _generate_temp_password()
        user = User(
            email=row["email"],
            hashed_password=await hash_password(temp_password),
            role=Role.student,
            first_name=row["first_name"],
            last_name=row["last_name"],
            phone=row.get("phone"),
            is_active=True,
        )
        db.add(user)
        await db.flush()

        student = Student(
            user_id=user.id,
            class_id=class_id,
            student_number=row.get("student_number"),
            photo_url=row.get("photo_url"),
            is_active=True,
        )
        db.add(student)
        created += 1

    await db.commit()
    return {"created": created, "skipped": skipped, "errors": errors}


async def get_class_students(db: AsyncSession, class_id: uuid.UUID) -> list[Student]:
    class_room = await db.get(Class, class_id)
    if not class_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")

    result = await db.scalars(
        select(Student).where(Student.class_id == class_id).options(selectinload(Student.user))
    )
    return list(result.all())


async def generate_project_groups(db: AsyncSession, class_id: uuid.UUID, group_size: int) -> list[ProjectGroup]:
    if group_size < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="group_size must be >= 1")

    class_room = await db.get(Class, class_id)
    if not class_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")

    students = list((await db.scalars(select(Student).where(Student.class_id == class_id).order_by(Student.id))).all())
    if not students:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No students found in class")

    old_groups = await db.scalars(select(ProjectGroup).where(ProjectGroup.class_id == class_id))
    for group in old_groups.all():
        await db.delete(group)
    await db.flush()

    num_groups = math.ceil(len(students) / group_size)
    groups: list[ProjectGroup] = []
    for index in range(num_groups):
        group = ProjectGroup(class_id=class_id, name=f"Group {index + 1}")
        db.add(group)
        groups.append(group)
    await db.flush()

    for index, student in enumerate(students):
        target_group = groups[index % num_groups]
        db.add(ProjectGroupMember(group_id=target_group.id, student_id=student.id))

    await db.commit()
    for group in groups:
        await db.refresh(group)
    return groups


async def get_class_project_groups(db: AsyncSession, class_id: uuid.UUID) -> list[ProjectGroup]:
    result = await db.scalars(
        select(ProjectGroup)
        .where(ProjectGroup.class_id == class_id)
        .options(selectinload(ProjectGroup.members))
        .order_by(ProjectGroup.created_at)
    )
    return list(result.all())


async def get_student_by_user(db: AsyncSession, user_id: uuid.UUID) -> Student:
    student = await db.scalar(select(Student).where(Student.user_id == user_id).options(selectinload(Student.user)))
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return student
