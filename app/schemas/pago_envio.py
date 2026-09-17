"""
Pydantic schemas para Pagos, Ventas y Envíos (v5 secciones 19, 20, 21, 22, 23, 24).
"""
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field


# --- PAGOS ---
class PagoCreateRequest(BaseModel):
    orden_venta_id: int
    tipo_pago: str = Field("en linea", description="'en linea' (PayPal) o 'en caja'")
    paypal_order_id: str | None = None
    paypal_capture_id: str | None = None


class PagoResponse(BaseModel):
    id: int
    orden_venta_id: int
    monto: Decimal
    tipo_pago: str
    estado: str
    paypal_order_id: str | None = None
    paypal_capture_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PayPalCrearOrdenRequest(BaseModel):
    orden_venta_id: int
    return_url: str | None = None
    cancel_url: str | None = None


class PayPalCapturarOrdenRequest(BaseModel):
    paypal_order_id: str
    orden_venta_id: int


class CobroCajaRequest(BaseModel):
    orden_venta_id: int
    efectivo_recibido: Decimal = Field(..., ge=0)


class CobroCajaResponse(BaseModel):
    pago_id: int
    orden_venta_id: int
    total: Decimal
    efectivo_recibido: Decimal
    cambio_devuelto: Decimal
    ticket_numero: str
    fecha: datetime


# --- ENVÍOS ---
class EnvioCotizacionRequest(BaseModel):
    distancia_km: float = Field(..., ge=0, description="Distancia estimada en kilómetros entre sucursal y destino")


class EnvioCreateRequest(BaseModel):
    orden_venta_id: int
    direccion: str = Field(..., min_length=5, max_length=255)
    ciudad: str = Field(..., min_length=2, max_length=100)
    referencia: str | None = None
    distancia_km: float | None = Field(None, ge=0)
    costo: Decimal | None = None


class EnvioUpdateRequest(BaseModel):
    direccion: str | None = None
    ciudad: str | None = None
    referencia: str | None = None
    costo: Decimal | None = None
    estado: str | None = None
    yango_tracking_code: str | None = None
    yango_tracking_url: str | None = None
    delivery_conductor: str | None = None


class EnvioYangoUpdateRequest(BaseModel):
    yango_tracking_code: str | None = None
    yango_tracking_url: str | None = None
    delivery_conductor: str | None = None
    estado: str | None = None


class EnvioResponse(BaseModel):
    id: int
    orden_venta_id: int
    direccion: str
    ciudad: str
    referencia: str | None = None
    costo: Decimal
    estado: str
    fecha: date
    yango_tracking_code: str | None = None
    yango_tracking_url: str | None = None
    delivery_conductor: str | None = None
    created_at: datetime
    cliente_nombre: str | None = None

    model_config = {"from_attributes": True}


# --- VENTAS ---
class VentaItemCreate(BaseModel):
    stock_inventario_id: int
    cantidad: int = Field(1, ge=1)


class VentaPresencialCreate(BaseModel):
    codigo_cliente: str
    sucursal_id: int
    items: list[VentaItemCreate] = Field(..., min_length=1)


class DetalleVentaResponse(BaseModel):
    id: int
    producto_nombre: str
    color_nombre: str | None = None
    talla_nombre: str | None = None
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal

    model_config = {"from_attributes": True}


class OrdenVentaResponse(BaseModel):
    id: int
    fecha: date
    estado: str
    total: Decimal
    tipo_venta: str
    codigo_cliente: str
    cliente_nombre: str | None = None
    cliente_email: str | None = None
    cliente_telefono: str | None = None
    sucursal_ciudad: str | None = None
    detalles: list[DetalleVentaResponse] = []
    envio: EnvioResponse | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
