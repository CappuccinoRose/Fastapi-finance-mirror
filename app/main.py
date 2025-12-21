# app/main.py

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from starlette.responses import FileResponse
from supabase import create_client, Client

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.exceptions import BusinessException, NotFoundException, ConflictException
from app.core.logging import setup_logging

# --- 获取 logger 实例 ---
logger = logging.getLogger(__name__)

# 在应用启动时配置日志
setup_logging()


# 加载环境变量
load_dotenv()

# 初始化 Supabase 客户端
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)


# --- 创建唯一的 FastAPI 应用实例 ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# --- 添加 CORS 中间件 ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:9925" ,
        "https://financemirror.icu",
        "https://www.financemirror.icu",
    ],
    allow_credentials=True,                   # 允许携带 cookie
    allow_methods=["*"],                      # 允许所有 HTTP 方法
    allow_headers=["*"],                      # 允许所有请求头
)

# --- 包含 API 路由 ---
app.include_router(api_router)

# --- 根路径处理器 ---
@app.get("/")
async def root():
    """根路径，返回欢迎信息和API文档链接"""
    return {
        "message": "Welcome to the Finance Mirror API!",
        "docs": "/docs",  # 指向FastAPI自动生成的API文档
        "health": "/health" # 指向健康检查端点
    }

@app.get("/favicon.ico")
async def favicon():
    return FileResponse("app/static/favicon.ico")

@app.get("/test-db")
async def test_database_connection():
    try:
        # 执行简单查询（例如查询 accounts 表，假设表存在）
        result = supabase.table("accounts").select("*").limit(1).execute()
        return {
            "status": "success",
            "message": "数据库连接正常",
            "data": result.data  # 返回查询结果（若表为空则返回 []）
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"连接失败: {str(e)}"
        }

# --- 健康检查端点 ---
@app.get("/health")
async def health_check():
    """健康检查端点，用于 Docker 健康检查"""
    return {"status": "healthy", "service": "Finance Mirror API"}


# --- 注册全局异常处理器 ---

# --- 处理 FastAPI 的 422 验证错误 ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # 使用 logger.error 记录详细的错误信息
    logger.error(
        f"Validation error for {request.method} {request.url}: {exc.errors()}"
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()}, # 保持与 FastAPI 默认返回格式一致
    )

# --- 处理 Pydantic 内部的验证错误 ---
@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    logger.error(
        f"Pydantic validation error for {request.method} {request.url}: {exc.errors()}"
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )

@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail, "type": "business_error"},
    )

@app.exception_handler(NotFoundException)
async def not_found_exception_handler(request: Request, exc: NotFoundException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail, "type": "not_found"},
    )

@app.exception_handler(ConflictException)
async def conflict_exception_handler(request: Request, exc: ConflictException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail, "type": "conflict"},
    )

@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"message": "数据库完整性错误，请检查数据关联。", "type": "integrity_error"},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # 记录未捕获的异常
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "服务器内部错误", "type": "internal_server_error"},
    )
