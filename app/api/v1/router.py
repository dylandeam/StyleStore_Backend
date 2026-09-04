"""
API v1 router — aggregates all v1 endpoint routers.
"""
from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.password import router as password_router
from app.api.v1.roles import router as roles_router
from app.api.v1.bitacora import router as bitacora_router
from app.api.v1.sucursales import router as sucursales_router
from app.api.v1.productos import router as productos_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(password_router)
api_v1_router.include_router(roles_router)
api_v1_router.include_router(bitacora_router)
api_v1_router.include_router(sucursales_router)
api_v1_router.include_router(productos_router)
