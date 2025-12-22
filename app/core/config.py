# app/core/config.py
# 核心配置文件
from pathlib import Path
from typing import Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 获取项目根目录的绝对路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# 在类定义之前定义默认值
DEFAULT_CORS_ORIGINS = ["*"]

class Settings(BaseSettings):
    PROJECT_NAME: str = "My Finance System API"

    # 数据库配置
    SQLALCHEMY_DATABASE_URI: str

    # JWT配置
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # 添加一个控制是否打印SQL语句的开关，开发时很有用
    SQLALCHEMY_ECHO: bool = False

    # 控制是否使用API前缀
    USE_API_PREFIX: bool = False

    # CORS 配置（可以是字符串，用逗号分隔，或者是列表）
    CORS_ORIGINS: Union[str, list[str]] = DEFAULT_CORS_ORIGINS

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v: Union[str, list[str]]) -> list[str]:
        """解析 CORS_ORIGINS 配置"""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            origins = [origin.strip() for origin in v.split(",") if origin.strip()]
            return origins if origins else DEFAULT_CORS_ORIGINS
        return DEFAULT_CORS_ORIGINS

    # Pydantic V2 配置，使用绝对路径指向 .env 文件
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra="ignore"
    )

# 创建一个全局的 settings 实例，应用启动时加载
settings = Settings()
