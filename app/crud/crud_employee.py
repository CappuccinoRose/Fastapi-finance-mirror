# app/crud/crud_employee.py

from typing import Any, Dict, Optional, Union
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import get_password_hash, verify_password
from app.crud.base import CRUDBase
from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.core.exceptions import ConflictException  # 确保这个自定义异常存在


class CRUDEmployee(CRUDBase[Employee, EmployeeCreate, EmployeeUpdate]):
    """
    员工数据访问层 (CRUD)
    提供创建、读取、更新、删除和认证等数据库操作。
    """

    async def get_by_username(self, db: AsyncSession, *, username: str) -> Optional[Employee]:
        """
        通过用户名获取员工信息。
        """
        statement = select(Employee).where(Employee.username == username)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self, db: AsyncSession, *, obj_in: Union[EmployeeCreate, Dict[str, Any]]
    ) -> Employee:
        """
        创建新员工。
        增强版：支持直接传入 Pydantic 模型或字典，并自动处理密码哈希。
        """
        # 1. 统一数据格式
        if isinstance(obj_in, dict):
            create_data = obj_in
        else:
            create_data = obj_in.model_dump(exclude_unset=True)

        # 2. 安全处理密码
        # 如果传入的数据中包含明文 'password'，则进行哈希处理
        if "password" in create_data and create_data["password"]:
            hashed_password = get_password_hash(create_data["password"])
            create_data["hashed_password"] = hashed_password
            # 从待存入字典中移除明文密码，防止泄露
            del create_data["password"]
        # 如果没有明文密码，但传入了 hashed_password，则直接使用
        elif "hashed_password" not in create_data:
            raise ValueError("创建员工时必须提供 'password' 或 'hashed_password'")

        # 3. 创建数据库对象并提交
        db_obj = Employee(**create_data)
        try:
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except IntegrityError as e:
            await db.rollback()
            # 捕获数据库唯一性约束冲突（如用户名重复）
            raise ConflictException(detail="用户名或ID已存在") from e
        except Exception as e:
            await db.rollback()
            raise e

    async def create_with_password(
        self, db: AsyncSession, *, username: str, password: str, **extra_fields
    ) -> Employee:
        """
        使用用户名和明文密码直接创建员工，适用于特定场景。
        """
        return await self.create(
            db,
            obj_in={
                "username": username,
                "password": password,
                **extra_fields
            }
        )

    async def authenticate(
        self, db: AsyncSession, *, username: str, password: str
    ) -> Optional[Employee]:
        """
        验证用户名和密码，返回用户对象或 None。
        """
        user = await self.get_by_username(db, username=username)
        if not user:
            return None
        if not user.active:
            return None  # 可以选择抛出 InactiveUserException
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: Employee,
        obj_in: Union[EmployeeUpdate, Dict[str, Any]]
    ) -> Employee:
        """
        更新员工信息。
        支持更新密码，并自动进行哈希处理。
        """
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)

        # 特殊处理密码更新
        if "password" in update_data and update_data["password"]:
            hashed_password = get_password_hash(update_data["password"])
            db_obj.hashed_password = hashed_password
            del update_data["password"] # 从更新字典中移除

        # 循环更新其他字段
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        try:
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except IntegrityError as e:
            await db.rollback()
            raise ConflictException(detail="更新失败，数据冲突（如用户名已被占用）。") from e
        except Exception as e:
            await db.rollback()
            raise e

    # 继承自 CRUDBase 的 `get`, `get_multi`, `remove` 方法通常无需重写
    # 如果有特殊需求，可以在这里重写它们


# 实例化 CRUD 对象，供其他模块导入使用
crud_employee = CRUDEmployee(Employee)

