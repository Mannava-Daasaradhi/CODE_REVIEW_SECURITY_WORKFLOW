from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # OpenAI API key — used by baseline script only, never by the environment server
    openai_api_key: str = ""

    # Episode data directory (relative to CWD — resolved at runtime)
    tasks_data_dir: str = "data/tasks"

    # Server bind settings
    env_host: str = "0.0.0.0"
    env_port: int = 7860

    # Logging
    log_level: str = "INFO"

    # Episode ordering seed — controls round-robin start when difficulty=None
    episode_seed: int = 42


settings = Settings()
