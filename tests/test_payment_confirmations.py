from decimal import Decimal

from app.core.security import hash_password
from app.models.cliente import Cliente
from app.models.empresa import Empresa
from app.models.notificacion import Notificacion
from app.models.orden_venta import OrdenVenta
from app.models.pago import Pago
from app.models.sucursal import Sucursal
from app.models.user import User
from app.services.pago_service import PagoService


def test_payment_confirmation_is_tenant_scoped_and_idempotent(db_session, monkeypatch):
    empresa = db_session.query(Empresa).filter(Empresa.codigo == "stylestore").one()
    sucursal = Sucursal(
        empresa_id=empresa.id,
        name="Sucursal Recibos",
        city="La Paz",
        address="Av. Recibos 10",
        phone="70001122",
        active=True,
    )
    user = User(
        empresa_id=empresa.id,
        email="recibos_cliente@stylestore.com",
        name="Cliente Recibo",
        hashed_password=hash_password("Pass123!"),
        role="cliente",
        is_active=True,
    )
    db_session.add_all([sucursal, user])
    db_session.flush()
    cliente = Cliente(
        codigo="CLI-RECIBO-IDEMP",
        user_id=user.id,
        telefono="70001122",
        direccion="Av. Recibos 10",
    )
    db_session.add(cliente)
    db_session.flush()
    orden = OrdenVenta(
        codigo_cliente=cliente.codigo,
        sucursal_id=sucursal.id,
        total=Decimal("125.50"),
        estado="pagada",
        tipo_venta="en linea",
    )
    db_session.add(orden)
    db_session.flush()
    pago = Pago(
        orden_venta_id=orden.id,
        empresa_id=empresa.id,
        monto=orden.total,
        tipo_pago="en linea",
        estado="aprobado",
    )
    db_session.add(pago)
    db_session.commit()

    enviados = []
    monkeypatch.setattr(
        "app.services.pago_service.send_notification_email",
        lambda **kwargs: enviados.append(kwargs) or True,
    )

    service = PagoService(db_session)
    service.confirmar(pago)
    recibo = pago.recibo_numero
    service.confirmar(pago)

    assert pago.empresa_id == empresa.id
    assert recibo == f"REC-{pago.id:08d}"
    assert pago.recibo_numero == recibo
    assert pago.email_confirmacion_intentos == 1
    assert pago.email_confirmacion_enviado_at is not None
    assert len(enviados) == 1
    notificaciones = db_session.query(Notificacion).filter(
        Notificacion.pago_id == pago.id,
        Notificacion.tipo == "pago_confirmado",
    ).all()
    assert len(notificaciones) == 1
    assert recibo in notificaciones[0].mensaje
