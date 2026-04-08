from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    # Used by baseline/run_baseline.py only — never read by the environment server
    gemini_api_key: str = ""
    tasks_data_dir: str = "data/tasks"
    log_level: str = "INFO"
    default_task_difficulty: str = "easy"


settings = Settings()
