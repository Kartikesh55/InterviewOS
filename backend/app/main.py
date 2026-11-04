import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError

from app.api.routes import ai, answers, health, interviews, questions
from app.core.config import get_settings
from app.core.exceptions import InterviewOSException
from app.schemas.common import ErrorResponse


logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title="InterviewOS API",
    description="Interview lifecycle, persistence, and internal AI workflows.",
    version="2.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(interviews.router)
app.include_router(questions.router)
app.include_router(answers.router)
app.include_router(ai.router)


@app.exception_handler(InterviewOSException)
async def handle_interviewos_exception(
    _request: Request,
    error: InterviewOSException,
) -> JSONResponse:
    response = ErrorResponse(message=error.message)
    return JSONResponse(
        status_code=error.status_code,
        content=response.model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def handle_request_validation(
    _request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    errors = [
        f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
        for item in error.errors()
    ]
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(message="Validation failed", errors=errors).model_dump(),
    )


@app.exception_handler(IntegrityError)
async def handle_integrity_conflict(
    _request: Request,
    error: IntegrityError,
) -> JSONResponse:
    logger.warning("Database constraint rejected a request", exc_info=error)
    return JSONResponse(
        status_code=409,
        content=ErrorResponse(
            message="The request conflicts with persisted interview data"
        ).model_dump(),
    )


@app.exception_handler(OperationalError)
async def handle_database_unavailable(
    _request: Request,
    error: OperationalError,
) -> JSONResponse:
    logger.error("Database operation failed", exc_info=error)
    return JSONResponse(
        status_code=503,
        content=ErrorResponse(message="Database is temporarily unavailable").model_dump(),
    )
