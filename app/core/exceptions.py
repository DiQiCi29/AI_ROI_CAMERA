from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def create_api_exception(status_code: int, code: str, message: str) -> HTTPException:
    """Helper function để tạo API exception với format chuẩn."""
    return HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message
        }
    )


def register_exception_handlers(app):
    """Đăng ký tất cả exception handlers cho ứng dụng FastAPI."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": detail.get("code", "INTERNAL_ERROR"),
                    "message": detail.get("message", str(exc.detail)),
                    "http_status": exc.status_code
                }
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "Request validation failed",
                    "details": exc.errors(),
                    "http_status": 400
                }
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "http_status": 500
                }
            }
        )
