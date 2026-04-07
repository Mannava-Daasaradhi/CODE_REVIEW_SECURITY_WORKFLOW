from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from app.config import settings
from app.environment.episode_loader import EpisodeLoader
from app.environment.env import Environment
from app.routes import reset, step, state


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: instantiate EpisodeLoader + Environment and attach to app.state.
    All routes access app.state.env — this is the only place it is created.
    """
    loader = EpisodeLoader()
    app.state.env = Environment(loader)
    logger.info("Environment initialised and attached to app.state.env")
    yield
    # No teardown needed — in-memory only


def create_app() -> FastAPI:
    application = FastAPI(
        title="PR Review & Security Audit OpenEnv Environment",
        description="OpenEnv-compliant environment for code review and security auditing.",
        version="1.0.0",
        lifespan=lifespan,
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
