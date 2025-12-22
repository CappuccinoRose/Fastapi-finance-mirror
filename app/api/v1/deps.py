# app/api/v1/deps.py
# 与数据库和认证的依赖配置
from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud.crud_employee import crud_employee
from app.db.session import AsyncSessionLocal
from app.schemas.user import UserWithAuth, TokenData
from app.core.exceptions import CredentialsException, InactiveUserException, PermissionDeniedException

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_db() -> Generator:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_current_user(
        db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> UserWithAuth: # 【修改】返回类型
    credentials_exception = CredentialsException()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = await crud_employee.get_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception

    return UserWithAuth.model_validate(user)


async def get_current_active_user(
        current_user: UserWithAuth = Depends(get_current_user),
) -> UserWithAuth:
    if not current_user.active:
        raise InactiveUserException()
    return current_user


async def get_current_active_superuser(
    current_user: UserWithAuth = Depends(get_current_active_user),
) -> UserWithAuth:
    """
    获取当前已激活的超级用户。
    如果用户不是超级用户，则抛出 403 Forbidden 错误。
    """
    if current_user.acl != "admin":
        raise PermissionDeniedException()
    return current_user
