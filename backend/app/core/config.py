from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # LLM 配置
    LLM_BASE_URL: str = "https://api.openai.com"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TIMEOUT: int = 30

    # 数据库配置
    DATABASE_URL: str = "sqlite:///./sales_agent.db"

    # JWT 安全配置 — 生产环境必须通过环境变量设置强密钥
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24

    # 应用配置
    APP_NAME: str = "客户攻单AI"
    API_V1_PREFIX: str = "/api/v1"

    class Config:
        env_file = ".env"


settings = Settings()