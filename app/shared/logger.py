"""
logger.py — Three-layer logging system.

Layer 1 — Event log (logs/events.log):
    Normal flow. INFO level. What happened.
    Use: logger.info("Pipeline started")

Layer 2 — Error log (logs/errors.log):
    Full traceback + local variable state at crash time. ERROR level.
    Use: logger.exception("what was being attempted when this broke")
    NEVER use logger.error() for exceptions — it drops the traceback.

Layer 3 — Audit log (logs/audit.jsonl):
    Structured JSON. One line per significant operation.
    Records: module, function, inputs, outputs, duration, status.
    Use: audit("module_name", "function_name", inputs={...}, result={...})
    This is what you read AFTER a bug to understand WHY it happened.

Quick reference:
    from src.shared.logger import logger, audit, log_call

    logger.info("something happened")
    logger.debug("verbose detail")
    logger.warning("something looks wrong but didn't crash")
    logger.exception("this was being attempted when it exploded")

    audit("quantum_core", "run_circuit", inputs={"n_qubits": 4}, result="ok", duration_ms=230)

    @log_call   # decorator — auto-logs entry, exit, duration, exceptions
    def my_function(x, y):
        ...
"""

import sys
import json
import time
import traceback
import functools
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger


# ── Paths ────────────────────────────────────────────────────────────────────
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

EVENT_LOG  = LOGS_DIR / "events.log"
ERROR_LOG  = LOGS_DIR / "errors.log"
AUDIT_LOG  = LOGS_DIR / "audit.jsonl"   # JSON Lines — one JSON object per line


# ── Layer 1 + 2: Loguru setup ─────────────────────────────────────────────────
def setup_logger(log_level: str = "INFO") -> None:
    """Configure loguru. Call once at startup (main.py does this)."""
    logger.remove()

    # Console — clean, human-readable
    logger.add(
        sys.stdout,
        level=log_level,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan> | "
            "{message}"
        ),
        colorize=True,
    )

    # Layer 1 — event log (INFO and above, no tracebacks)
    logger.add(
        EVENT_LOG,
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        filter=lambda record: record["level"].name != "ERROR",
    )

    # Layer 2 — error log (ERROR only, WITH full tracebacks + locals)
    logger.add(
        ERROR_LOG,
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="30 days",     # keep errors longer
        compression="zip",
        backtrace=True,          # full traceback
        diagnose=True,           # capture local variable values at crash point
    )


# ── Layer 3: Audit log ────────────────────────────────────────────────────────
def audit(
    module: str,
    operation: str,
    *,
    inputs: dict[str, Any] | None = None,
    result: Any = None,
    status: str = "ok",          # "ok" | "error" | "skipped"
    duration_ms: float | None = None,
    error: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """
    Write one structured JSON line to audit.jsonl.

    Every significant operation should call this — it's what lets you
    reconstruct exactly what happened in what order when debugging.

    Example:
        audit(
            "quantum_core", "run_circuit",
            inputs={"n_qubits": 4, "shots": 1024, "backend": "default.qubit"},
            result={"energy": -1.137, "converged": True},
            duration_ms=340.2,
        )
    """
    record: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "module": module,
        "op": operation,
        "status": status,
    }
    if inputs is not None:
        record["inputs"] = _safe_serialize(inputs)
    if result is not None:
        record["result"] = _safe_serialize(result)
    if duration_ms is not None:
        record["duration_ms"] = round(duration_ms, 2)
    if error is not None:
        record["error"] = str(error)
    if extra:
        record["extra"] = _safe_serialize(extra)

    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _safe_serialize(obj: Any) -> Any:
    """Convert obj to JSON-safe form without crashing on complex types."""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    if isinstance(obj, dict):
        return {str(k): _safe_serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe_serialize(i) for i in obj]
    # Numpy arrays, tensors, etc. — just store shape + dtype
    if hasattr(obj, "shape") and hasattr(obj, "dtype"):
        return {"__type__": type(obj).__name__, "shape": list(obj.shape), "dtype": str(obj.dtype)}
    return {"__type__": type(obj).__name__, "__repr__": repr(obj)[:200]}


# ── Decorator: auto-audit any function ───────────────────────────────────────
def log_call(fn=None, *, module: str | None = None, audit_inputs: bool = True):
    """
    Decorator that auto-logs entry, exit, duration, and exceptions.

    Usage:
        @log_call
        def train_model(config): ...

        @log_call(module="quantum_core", audit_inputs=False)  # hide inputs (e.g. secrets)
        def generate_key(secret): ...
    """
    def decorator(func):
        mod = module or func.__module__.split(".")[-1]

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            inputs = {}
            if audit_inputs:
                try:
                    import inspect
                    sig = inspect.signature(func)
                    bound = sig.bind(*args, **kwargs)
                    bound.apply_defaults()
                    inputs = dict(bound.arguments)
                except Exception:
                    inputs = {"__note__": "could not capture inputs"}

            logger.debug(f"{mod}.{func.__name__} — start")
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start) * 1000
                audit(mod, func.__name__, inputs=inputs,
                      result=result, status="ok", duration_ms=duration_ms)
                logger.debug(f"{mod}.{func.__name__} — done ({duration_ms:.1f}ms)")
                return result
            except Exception as exc:
                duration_ms = (time.perf_counter() - start) * 1000
                audit(mod, func.__name__, inputs=inputs,
                      status="error", duration_ms=duration_ms,
                      error=f"{type(exc).__name__}: {exc}")
                # Use exception() not error() — captures full traceback + locals
                logger.exception(
                    f"{mod}.{func.__name__} — FAILED after {duration_ms:.1f}ms | "
                    f"{type(exc).__name__}: {exc}"
                )
                raise  # always re-raise — never silently swallow
        return wrapper

    return decorator(fn) if fn is not None else decorator


# ── Convenience: read audit log for debugging ─────────────────────────────────
def tail_audit(n: int = 20) -> list[dict]:
    """Return the last n audit log entries. Useful in notebooks for debugging."""
    if not AUDIT_LOG.exists():
        return []
    lines = AUDIT_LOG.read_text().strip().splitlines()
    return [json.loads(line) for line in lines[-n:]]


def audit_errors() -> list[dict]:
    """Return all audit entries with status='error'. Quick failure report."""
    if not AUDIT_LOG.exists():
        return []
    entries = [json.loads(line) for line in AUDIT_LOG.read_text().strip().splitlines() if line]
    return [e for e in entries if e.get("status") == "error"]


# ── Initialize on import ──────────────────────────────────────────────────────
setup_logger()

__all__ = ["logger", "audit", "log_call", "setup_logger", "tail_audit", "audit_errors"]
