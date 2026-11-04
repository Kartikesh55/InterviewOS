from fastapi import APIRouter


router = APIRouter(tags=["health"])


@router.get("/api/health")
def health_check() -> dict[str, str]:
    return {
        "status": "UP",
        "service": "InterviewOS Backend",
    }


@router.get("/api/ai/health", include_in_schema=False)
def ai_health_check() -> dict[str, str]:
    return {
        "status": "UP",
        "service": "InterviewOS AI Service",
    }
