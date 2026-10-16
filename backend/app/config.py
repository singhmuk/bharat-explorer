from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "mysql+pymysql://app:app@mysql:3306/bharat?charset=utf8mb4"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = "change-me"
    jwt_hours: int = 24 * 7
    # anthropic_api_key: str = ""
    # llm_model: str = "claude-sonnet-5-5"
    ollama_url: str = "http://localhost:11434"
    llm_model: str = "llama3.2"
    cors_origins: str = "http://localhost:5173"
    # anti-scraping
    rate_limit_per_minute: int = 60
    max_distinct_pages_per_minute: int = 25
    ban_seconds: int = 3600
    free_itineraries_per_day: int = 2

    class Config:
        env_file = ".env"


settings = Settings()
