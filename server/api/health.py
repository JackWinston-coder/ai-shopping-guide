from fastapi import APIRouter

from server.db import database as db_module

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health():
    checks = {"status": "ok", "database": "disconnected"}
    conn = db_module._db_connection
    if conn is not None:
        try:
            await conn.execute("SELECT 1")
            checks["database"] = "connected"
        except Exception:
            checks["database"] = "error"
            checks["status"] = "degraded"
    return checks
