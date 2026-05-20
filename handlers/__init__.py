from .auth import router as auth_router
from .client import router as client_router
from .booking import router as booking_router
from .doctor import router as doctor_router
from .admin import router as admin_router

__all__ = ["auth_router", "client_router", "booking_router", "doctor_router", "admin_router"]