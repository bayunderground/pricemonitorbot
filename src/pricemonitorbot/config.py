from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    BOT_TOKEN: str
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/pricemonitorbot"
    LOG_LEVEL: str = "INFO"
    SCHEDULER_TIMEZONE: str = "Europe/Moscow"
    WB_PARSE_INTERVAL_HOURS: int = 1
    ADMIN_CHAT_ID: int | None = None


settings = Settings()
