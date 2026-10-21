import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Base directory for the NXT project
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

class Settings(BaseSettings):
    GROQ_API_KEY: str = Field(default="", description="Groq API key")
    GROQ_MODEL: str = Field(default="openai/gpt-oss-120b", description="Model for lesson generation")
    GROQ_JUDGE_MODEL: str = Field(default="openai/gpt-oss-120b", description="Model for LLM-as-a-Judge evaluation")
    
    LANGSMITH_TRACING: bool = Field(default=False, description="Enable LangSmith tracing")
    LANGSMITH_API_KEY: str = Field(default="", description="LangSmith API Key")
    LANGSMITH_PROJECT: str = Field(default="self-evaluating-lesson-generator", description="LangSmith project name")
    
    ENVIRONMENT: str = Field(default="development", description="Runtime environment")
    DATABASE_PATH: str = Field(default=str(BASE_DIR / "data" / "app.db"), description="Path to SQLite database")
    PORT: int = Field(default=8000, description="Backend API port")
    HOST: str = Field(default="127.0.0.1", description="Backend API host")
    MAX_RETRIES: int = Field(default=2, ge=1, le=2, description="Maximum content retries (exactly 1 or 2 per specification)")
    LOG_LEVEL: str = Field(default="INFO", description="Log level")
    
    # Target audience configuration
    TARGET_AUDIENCE: str = (
        "A person who has completed class 12 in India, with limited English vocabulary, "
        "possibly from a non-English-medium background, starting from zero AI knowledge, aiming to start an AI career."
    )

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_redacted_groq_key(self) -> str:
        if not self.GROQ_API_KEY:
            return "<UNSET>"
        if len(self.GROQ_API_KEY) <= 8:
            return "****"
        return f"{self.GROQ_API_KEY[:4]}...{self.GROQ_API_KEY[-4:]}"

settings = Settings()

# Ensure data directory exists
os.makedirs(os.path.dirname(settings.DATABASE_PATH), exist_ok=True)
