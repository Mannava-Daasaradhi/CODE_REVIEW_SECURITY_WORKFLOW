from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from loguru import logger

from app.config import settings
from app.environment.episode_loader import EpisodeLoader
from app.environment.env import Environment
from app.models.action import Action
from app.models.observation import Observation
from app.models.state import EnvironmentState
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

    @application.get("/")
    async def root() -> dict:
        return {"status": "ok"}

    @application.get("/health")
    async def health() -> dict:
        # FIX: openenv validate requires {"status": "healthy"}, not "ok"
        return {"status": "healthy"}

    @application.get("/metadata")
    async def metadata() -> dict:
        # NEW: required by openenv validate
        return {
            "name": "pr-review-security-audit",
            "description": (
                "OpenEnv environment for training and evaluating AI agents on code review "
                "and security auditing tasks. Three difficulty tiers with deterministic graders."
            ),
            "version": "1.0.0",
            "author": "Harshithd10",
            "tasks": ["task1 (easy)", "task2 (medium)", "task3 (hard)"],
        }

    @application.get("/schema")
    async def schema() -> dict:
        # NEW: required by openenv validate — returns Pydantic JSON schemas for all models
        return {
            "action": Action.model_json_schema(),
            "observation": Observation.model_json_schema(),
            "state": EnvironmentState.model_json_schema(),
        }

    @application.post("/mcp")
    async def mcp(request: Request) -> Any:
        # NEW: required by openenv validate — minimal MCP (Model Context Protocol) handler
        # Returns JSON-RPC 2.0 payloads as required by the OpenEnv spec
        body = await request.json()
        method = body.get("method", "")
        req_id = body.get("id", 1)

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "pr-review-security-audit",
                        "version": "1.0.0",
                    },
                },
            }

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": "reset",
                            "description": (
                                "Start a new episode. Returns an Observation with "
                                "code snippet and task instructions."
                            ),
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "task_difficulty": {
                                        "type": "string",
                                        "enum": ["easy", "medium", "hard"],
                                        "description": (
                                            "Difficulty tier. Omit to cycle round-robin."
                                        ),
                                    }
                                },
                            },
                        },
                        {
                            "name": "step",
                            "description": (
                                "Submit agent analysis for the current episode. "
                                "Returns reward (float 0–1) and step result."
                            ),
                            "inputSchema": Action.model_json_schema(),
                        },
                        {
                            "name": "state",
                            "description": "Get current environment state for debugging.",
                            "inputSchema": {"type": "object", "properties": {}},
                        },
                    ]
                },
            }

        # Unknown method — return a valid JSON-RPC error response (still HTTP 200
        # so the validator can see the jsonrpc field and confirm the endpoint works)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }

    logger.info(f"App created | log_level={settings.log_level}")
    return application


app = create_app()
