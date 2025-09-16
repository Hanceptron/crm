"""
Middleware configuration for the Aviation Workflow System.

Provides CORS, logging, error handling, and request tracing middleware
for the FastAPI application.
"""

import time
import uuid
import logging
from typing import Callable
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from core.config import settings

# Set up logging
logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add unique request IDs for tracing.
    
    Adds a unique X-Request-ID header to all requests and responses
    for easier debugging and log correlation.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with unique ID."""
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Add request ID to request state for access in endpoints
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request/response logging.
    
    Logs all HTTP requests with timing information, status codes,
    and request IDs for debugging and monitoring.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response information."""
        start_time = time.time()
        
        # Get request ID from state (set by RequestIDMiddleware)
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Log incoming request
        logger.info(
            f"Request started - {request.method} {request.url.path} "
            f"[{request_id}] from {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                f"Request completed - {request.method} {request.url.path} "
                f"[{request_id}] {response.status_code} in {process_time:.3f}s"
            )
            
            # Add timing header
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # Calculate processing time for errors
            process_time = time.time() - start_time
            
            # Log error
            logger.error(
                f"Request failed - {request.method} {request.url.path} "
                f"[{request_id}] error in {process_time:.3f}s: {str(e)}"
            )
            
            # Re-raise the exception to be handled by error middleware
            raise


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware.
    
    Catches unhandled exceptions and returns consistent error responses
    with proper HTTP status codes and error messages.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle errors and return consistent error responses."""
        try:
            return await call_next(request)
            
        except HTTPException:
            # Re-raise HTTP exceptions to be handled by FastAPI
            raise
            
        except ValueError as e:
            # Handle validation errors
            logger.warning(f"Validation error: {str(e)}")
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Validation Error",
                    "detail": str(e),
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
            
        except PermissionError as e:
            # Handle permission errors
            logger.warning(f"Permission error: {str(e)}")
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Permission Denied",
                    "detail": str(e),
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
            
        except FileNotFoundError as e:
            # Handle not found errors
            logger.warning(f"Not found error: {str(e)}")
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Not Found",
                    "detail": str(e),
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
            
        except ConnectionError as e:
            # Handle database/external service connection errors
            logger.error(f"Connection error: {str(e)}")
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Service Unavailable",
                    "detail": "Unable to connect to required services",
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
            
        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "detail": "An unexpected error occurred" if not settings.debug else str(e),
                    "request_id": getattr(request.state, "request_id", None)
                }
            )


def configure_cors(app: FastAPI) -> None:
    """
    Configure CORS middleware for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Request-ID",
            "X-API-Key"
        ],
        expose_headers=["X-Request-ID", "X-Process-Time"]
    )


def configure_middleware(app: FastAPI) -> None:
    """
    Configure all middleware for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Configure CORS (must be first for preflight requests)
    configure_cors(app)
    
    # Add custom middleware in reverse order (last added = first executed)
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to responses.
    
    Adds common security headers to protect against various attacks.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)
        
        # Add security headers
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'",
        }
        
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response


def configure_production_middleware(app: FastAPI) -> None:
    """
    Configure additional middleware for production deployment.
    
    Args:
        app: FastAPI application instance
    """
    # Add security headers in production
    if settings.is_production:
        app.add_middleware(SecurityHeadersMiddleware)


# Custom exception handlers

async def validation_exception_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle validation exceptions with consistent format."""
    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation Error",
            "detail": str(exc),
            "request_id": getattr(request.state, "request_id", None)
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions with consistent format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail if isinstance(exc.detail, str) else "HTTP Error",
            "detail": exc.detail,
            "request_id": getattr(request.state, "request_id", None)
        }
    )


def configure_exception_handlers(app: FastAPI) -> None:
    """
    Configure exception handlers for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(ValueError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)


# Rate limiting middleware (optional for production)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware.
    
    Implements basic rate limiting based on client IP address.
    For production, consider using Redis-based rate limiting.
    """
    
    def __init__(self, app: ASGIApp, calls: int = 100, period: int = 60):
        """
        Initialize rate limiting middleware.
        
        Args:
            app: ASGI application
            calls: Number of calls allowed per period
            period: Period in seconds
        """
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = {}  # In production, use Redis
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting."""
        if not settings.is_production:
            # Skip rate limiting in development
            return await call_next(request)
        
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Clean old entries
        self.clients = {
            ip: (count, timestamp) 
            for ip, (count, timestamp) in self.clients.items()
            if current_time - timestamp < self.period
        }
        
        # Check rate limit
        if client_ip in self.clients:
            count, timestamp = self.clients[client_ip]
            if current_time - timestamp < self.period and count >= self.calls:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Too Many Requests",
                        "detail": f"Rate limit exceeded: {self.calls} calls per {self.period} seconds",
                        "request_id": getattr(request.state, "request_id", None)
                    }
                )
        
        # Update rate limit counter
        if client_ip in self.clients:
            count, _ = self.clients[client_ip]
            self.clients[client_ip] = (count + 1, current_time)
        else:
            self.clients[client_ip] = (1, current_time)
        
        return await call_next(request)