from fastapi import APIRouter


health_router = APIRouter()


@health_router.get("/health-check", status_code=200)
async def health_check():
    # This function must return successfully and not use any dependencies.
    return {"status": "ok", "app": "running"}
