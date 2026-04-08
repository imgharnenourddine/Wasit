from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import blacklist_token
from app.models.user import User
from app.schemas.auth import Token, TokenRefresh, UserCreate, UserLogin, UserResponse
from app.services.auth_service import login, refresh_token, register

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    user = await register(db, payload)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=Token)
async def login_user(
    payload: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    return await login(db, payload.email, payload.password)


@router.post("/refresh", response_model=Token)
async def refresh_user_token(
    payload: TokenRefresh,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    return await refresh_token(db, payload.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.post("/logout")
async def logout(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> dict[str, str]:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    await blacklist_token(token)
    return {"message": "Logged out successfully"}
