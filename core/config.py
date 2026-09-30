from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List, Optional
import os

class Settings(BaseSettings):
    # Telegram Bot
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    admin_telegram_ids_raw: str = Field(default="", alias="ADMIN_TELEGRAM_IDS")
    telegram_proxy: Optional[str] = Field(default=None, alias="TELEGRAM_PROXY")
    
    # Environment & Service
    environment: str = Field(default="development", alias="ENVIRONMENT")
    humatron_api_base_url: str = Field(default="https://humatron.me", alias="HUMATRON_API_BASE_URL")
    humatron_secret_key: str = Field(default="super-secret-humatron-key-2026", alias="HUMATRON_SECRET_KEY")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres@localhost:5432/humatron_db",
        alias="DATABASE_URL"
    )
    
    # Webhook
    use_webhook: bool = Field(default=False, alias="USE_WEBHOOK")
    telegram_webhook_url: str = Field(default="https://humatron.me/api/telegram-webhook", alias="TELEGRAM_WEBHOOK_URL")
    telegram_webhook_secret: str = Field(default="", alias="TELEGRAM_WEBHOOK_SECRET")
    
    # PDF Constraints
    max_pdf_size_mb: int = Field(default=20, alias="MAX_PDF_SIZE_MB")
    max_pdf_pages: int = Field(default=300, alias="MAX_PDF_PAGES")
    temp_upload_dir: str = Field(default="temp_uploads", alias="TEMP_UPLOAD_DIR")
    
    # Payment Gateways (Optional sandbox credentials)
    telebirr_app_id: Optional[str] = Field(default=None, alias="TELEBIRR_APP_ID")
    telebirr_app_key: Optional[str] = Field(default=None, alias="TELEBIRR_APP_KEY")
    telebirr_short_code: Optional[str] = Field(default=None, alias="TELEBIRR_SHORT_CODE")
    binance_pay_api_key: Optional[str] = Field(default=None, alias="BINANCE_PAY_API_KEY")
    binance_pay_secret_key: Optional[str] = Field(default=None, alias="BINANCE_PAY_SECRET_KEY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def admin_telegram_ids(self) -> List[int]:
        if not self.admin_telegram_ids_raw:
            return []
        ids = []
        for x in self.admin_telegram_ids_raw.split(","):
            trimmed = x.strip()
            if trimmed.isdigit():
                ids.append(int(trimmed))
        return ids

settings = Settings()
