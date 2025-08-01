import os
from typing import Optional

class Settings:
    """系統設定類別"""
    
    # 資料庫設定
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "sms_system")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
    
    # FastAPI設定
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # SMS Gateway設定
    SMS_GATEWAY_URL: str = os.getenv("SMS_GATEWAY_URL", "http://123.123.123.123:4321/mpsiweb/smssubmit")
    SMS_SYS_ID: str = os.getenv("SMS_SYS_ID", "ENT001")
    SMS_SRC_ADDRESS: str = os.getenv("SMS_SRC_ADDRESS", "01234500000000001234")
    SMS_DR_FLAG: bool = os.getenv("SMS_DR_FLAG", "true").lower() == "true"
    SMS_FIRST_FAIL_FLAG: bool = os.getenv("SMS_FIRST_FAIL_FLAG", "false").lower() == "true"
    
    # AI服務設定
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "gemini")  # 可選值: "gemini" 或 "openai"
    
    # Gemini API設定
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "XXXXXXXXXX")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    
    # OpenAI API設定
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "sk-or-v1-XXXXXXXXXXX")
    OPENAI_API_BASE: str = os.getenv("OPEN_BASE_URL", "https://openrouter.ai/api/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "mistralai/mistral-small-3.1-24b-instruct:free")
    
    # 日誌設定
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/sms_system.log")
    LOG_MAX_SIZE: int = int(os.getenv("LOG_MAX_SIZE", "10485760"))  # 10MB
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    
    # 排程設定
    SCHEDULE_INTERVAL: int = int(os.getenv("SCHEDULE_INTERVAL", "60"))  # 秒
    
    # 簡訊設定
    SMS_MAX_LENGTH: int = 70
    SMS_MAX_LENGTH_EXTENDED: int = 140
    
    @property
    def DATABASE_URL(self) -> str:
        """PostgreSQL連線字串"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

# 建立全域設定實例
settings = Settings()
