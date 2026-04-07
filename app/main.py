from fastapi import FastAPI
from loguru import logger
from app.config import settings
from app.routes import reset, step, state

def create_app() -> FastAPI:
    application = FastAPI(
        title="PR Review & Security Audit OpenEnv Environment",
        description="OpenEnv-compliant environment for code review and security auditing.",
        version="1.0.0",
    )
    application.include_router(reset.router)
    application.include_router(step.router)
    application.include_router(state.router)

    @application.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    logger.info(f"App created | log_level={settings.log_level}")
    return application

app = create_app()
