from typing import List, Dict, Any
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app import schemas
from app.api.v1 import deps
from app.crud import crud_customer, crud_invoice, crud_entry
from app.schemas.user import User
from app.core.exceptions import ConflictException

router = APIRouter()


@router.get("/sales-invoices", response_model=List[schemas.Invoice], summary="获取销售发票列表")
async def read_sales_invoices(
        db: AsyncSession = Depends(deps.get_db),
        skip: int = 0,
        limit: int = 100,
        current_user: User = Depends(deps.get_current_active_user)
):
    return await crud_invoice.get_multi(db, skip=skip, limit=limit)


@router.post("/sales-invoices", response_model=schemas.Invoice, summary="创建销售发票",
             status_code=status.HTTP_201_CREATED)
async def create_sales_invoice(
        *,
        db: AsyncSession = Depends(deps.get_db),
        invoice_in: schemas.InvoiceCreate,
        current_user: User = Depends(deps.get_current_active_user)
):
    return await crud_invoice.create(db, obj_in=invoice_in)


@router.get("/sales-invoices/{guid}", response_model=schemas.Invoice, summary="获取单个销售发票详情")
async def read_sales_invoice(
        *,
        db: AsyncSession = Depends(deps.get_db),
        guid: str,
        current_user: User = Depends(deps.get_current_active_user)
):
    invoice = await crud_invoice.get(db, id=guid)  # 移除 options 参数
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="发票未找到")
    return invoice



@router.put("/sales-invoices/{guid}", response_model=schemas.Invoice, summary="更新销售发票")
async def update_sales_invoice(
        *,
        db: AsyncSession = Depends(deps.get_db),
        guid: str,
        invoice_in: schemas.InvoiceUpdate,
        current_user: User = Depends(deps.get_current_active_user)
):
    db_invoice = await crud_invoice.get(db, id=guid)
    if not db_invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="发票未找到")
    return await crud_invoice.update(db=db, db_obj=db_invoice, obj_in=invoice_in)


@router.post("/sales-invoices/{guid}/void", status_code=status.HTTP_204_NO_CONTENT, summary="作废销售发票")
async def void_sales_invoice(
        *,
        db: AsyncSession = Depends(deps.get_db),
        guid: str,
        current_user: User = Depends(deps.get_current_active_user)
):
    db_invoice = await crud_invoice.get(db, id=guid)
    if not db_invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="发票未找到")
    if not db_invoice.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="发票已经被作废")
    await crud_invoice.update(db=db, db_obj=db_invoice, obj_in={"active": False})


@router.post("/sales-invoices/{guid}/unvoid", response_model=schemas.Invoice, summary="取消作废销售发票")
async def unvoid_sales_invoice(
        *,
        db: AsyncSession = Depends(deps.get_db),
        guid: str,
        current_user: User = Depends(deps.get_current_active_user)
):
    db_invoice = await crud_invoice.get(db, id=guid)
    if not db_invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="发票未找到")
    if db_invoice.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="发票未被作废，无需取消")
    updated_invoice = await crud_invoice.update(db=db, db_obj=db_invoice, obj_in={"active": True})
    return updated_invoice


@router.post("/sales-invoices/{guid}/send", response_model=schemas.Invoice, summary="发送销售发票")
async def send_sales_invoice(
        *,
        db: AsyncSession = Depends(deps.get_db),
        guid: str,
        current_user: User = Depends(deps.get_current_active_user)
):
    db_invoice = await crud_invoice.get(db, id=guid)
    if not db_invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="发票未找到")
    if not db_invoice.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能发送已作废的发票")
    return db_invoice

@router.get("/customers", response_model=List[schemas.Customer], summary="获取客户列表")
async def read_customers(
        db: AsyncSession = Depends(deps.get_db),
        skip: int = 0,
        limit: int = 100,
        current_user: User = Depends(deps.get_current_active_user)
):
    return await crud_customer.get_multi(db, skip=skip, limit=limit)

@router.post("/customers", response_model=schemas.Customer, summary="创建新客户", status_code=status.HTTP_201_CREATED)
async def create_customer(
        *,
        db: AsyncSession = Depends(deps.get_db),
        customer_in: schemas.CustomerCreate,
        current_user: User = Depends(deps.get_current_active_user)
):
    customer = await crud_customer.get_by_name(db, name=customer_in.name)
    if customer:
        raise ConflictException(detail="客户名称已存在")
    return await crud_customer.create(db=db, obj_in=customer_in)

@router.get("/customers/{guid}", response_model=schemas.Customer, summary="获取单个客户详情")
async def read_customer(
        *,
        db: AsyncSession = Depends(deps.get_db),
        guid: str,
        current_user: User = Depends(deps.get_current_active_user)
):
    customer = await crud_customer.get(db, id=guid)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客户未找到")
    return customer

@router.put("/customers/{guid}", response_model=schemas.Customer, summary="更新客户信息")
async def update_customer(
        *,
        db: AsyncSession = Depends(deps.get_db),
        guid: str,
        customer_in: schemas.CustomerUpdate,
        current_user: User = Depends(deps.get_current_active_user)
):
    customer = await crud_customer.get(db, id=guid)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客户未找到")
    if customer_in.name and customer_in.name != customer.name:
        existing_customer = await crud_customer.get_by_name(db, name=customer_in.name)
        if existing_customer:
            raise ConflictException(detail="新的客户名称已被其他客户使用")
    return await crud_customer.update(db=db, db_obj=customer, obj_in=customer_in)

@router.delete("/customers/{guid}", status_code=status.HTTP_204_NO_CONTENT, summary="删除客户")
async def delete_customer(
        *,
        db: AsyncSession = Depends(deps.get_db),
        guid: str,
        current_user: User = Depends(deps.get_current_active_user)
):
    customer = await crud_customer.get(db, id=guid)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客户未找到")
    if not customer.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="客户已经被禁用")
    await crud_customer.update(db=db, db_obj=customer, obj_in={"active": False})

