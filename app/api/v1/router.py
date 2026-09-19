"""
API v1 router — aggregates all v1 endpoint routers.
Conforme a Especificación StyleStore v5.
"""
from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.password import router as password_router
from app.api.v1.roles import router as roles_router
from app.api.v1.bitacora import router as bitacora_router
from app.api.v1.sucursales import router as sucursales_router
from app.api.v1.productos import router as productos_router

from app.api.v1.empleados import router as empleados_router
from app.api.v1.clientes import router as clientes_router
from app.api.v1.categorias import router as categorias_router
from app.api.v1.colores import router as colores_router
from app.api.v1.tallas import router as tallas_router
from app.api.v1.temporadas import router as temporadas_router
from app.api.v1.colecciones import router as colecciones_router
from app.api.v1.proximamente import router as proximamente_router
from app.api.v1.proveedores import router as proveedores_router
from app.api.v1.catalogo import router as catalogo_router
from app.api.v1.reservas import router as reservas_router
from app.api.v1.carrito import router as carrito_router
from app.api.v1.pagos import router as pagos_router
from app.api.v1.envios import router as envios_router
from app.api.v1.ventas import router as ventas_router
from app.api.v1.inventario import router as inventario_router
from app.api.v1.uploads import router as uploads_router
from app.api.v1.backups import router as backups_router
from app.api.v1.reportes import router as reportes_router
from app.api.v1.notificaciones import router as notificaciones_router
from app.api.v1.cambios import router as cambios_router
from app.api.v1.chatbot import router as chatbot_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(password_router)
api_v1_router.include_router(roles_router)
api_v1_router.include_router(bitacora_router)
api_v1_router.include_router(sucursales_router)
api_v1_router.include_router(productos_router)

api_v1_router.include_router(empleados_router)
api_v1_router.include_router(clientes_router)
api_v1_router.include_router(categorias_router)
api_v1_router.include_router(colores_router)
api_v1_router.include_router(tallas_router)
api_v1_router.include_router(temporadas_router)
api_v1_router.include_router(colecciones_router)
api_v1_router.include_router(proximamente_router)
api_v1_router.include_router(proveedores_router)

api_v1_router.include_router(catalogo_router)
api_v1_router.include_router(reservas_router)
api_v1_router.include_router(carrito_router)
api_v1_router.include_router(pagos_router)
api_v1_router.include_router(envios_router)
api_v1_router.include_router(ventas_router)
api_v1_router.include_router(inventario_router)
api_v1_router.include_router(uploads_router)
api_v1_router.include_router(backups_router)
api_v1_router.include_router(reportes_router)
api_v1_router.include_router(notificaciones_router)
api_v1_router.include_router(cambios_router)
api_v1_router.include_router(chatbot_router)
