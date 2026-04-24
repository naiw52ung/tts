from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "LegendAI Builder API"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 60 * 24
    database_url: str = "postgresql+psycopg2://legendai:legendai@postgres:5432/legendai"
    redis_url: str = "redis://redis:6379/0"
    celery_task_always_eager: bool = False
    celery_task_eager_propagates: bool = True
    storage_root: str = "/data/storage"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    admin_api_key: str = ""


settings = Settings()
