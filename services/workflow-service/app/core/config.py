from pydantic_settings import BaseSettings 

class Settings(BaseSettings):
    PROJECT_NAME: str = "JNPI Core Ticketing API"
    DATABASE_URL: str = "postgresql://jnpi:jnpi_password@localhost:5432/workflow_db"
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
