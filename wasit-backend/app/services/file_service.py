import csv
from asyncio import to_thread
from io import StringIO

import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)


async def parse_trombinoscope_csv(file: UploadFile) -> list[dict]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only CSV files are supported")

    content = await file.read()
    await file.seek(0)
    decoded = content.decode("utf-8-sig")
    reader = csv.DictReader(StringIO(decoded))
    required = {"student_number", "first_name", "last_name", "email", "phone", "photo_url"}

    if not reader.fieldnames:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV file is empty")
    if not required.issubset(set(reader.fieldnames)):
        missing = sorted(list(required.difference(set(reader.fieldnames))))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required CSV columns: {', '.join(missing)}",
        )

    rows: list[dict] = []
    errors: list[dict] = []
    for index, row in enumerate(reader, start=2):
        if not row.get("first_name") or not row.get("last_name") or not row.get("email"):
            errors.append({"line": index, "error": "first_name, last_name, and email are required"})
            continue
        rows.append(
            {
                "student_number": (row.get("student_number") or "").strip() or None,
                "first_name": row["first_name"].strip(),
                "last_name": row["last_name"].strip(),
                "email": row["email"].strip().lower(),
                "phone": (row.get("phone") or "").strip() or None,
                "photo_url": (row.get("photo_url") or "").strip() or None,
            }
        )

    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Invalid rows found in CSV", "errors": errors},
        )
    return rows


async def save_upload(file: UploadFile, destination_folder: str) -> str:
    content = await file.read()
    await file.seek(0)
    safe_name = file.filename or "upload.csv"
    folder = destination_folder.replace("\\", "/").strip("/")

    result = await to_thread(
        cloudinary.uploader.upload,
        content,
        resource_type="raw",
        folder=folder,
        public_id=safe_name.rsplit(".", 1)[0],
        overwrite=True,
    )
    return str(result["secure_url"])


async def save_image_upload(file: UploadFile, destination_folder: str) -> str:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only image files are supported")

    content = await file.read()
    await file.seek(0)
    safe_name = file.filename or "image"
    folder = destination_folder.replace("\\", "/").strip("/")

    result = await to_thread(
        cloudinary.uploader.upload,
        content,
        resource_type="image",
        folder=folder,
        public_id=safe_name.rsplit(".", 1)[0],
        overwrite=True,
    )
    return str(result["secure_url"])
