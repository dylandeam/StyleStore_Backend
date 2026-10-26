"""Generate a rollback-only branded catalog used for visual PDF QA."""
from decimal import Decimal
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.categoria import Categoria
from app.models.empresa import Empresa
from app.models.producto import Producto
from app.models.temporada import Temporada
from app.models.user import User
from app.services.catalog_pdf_service import CatalogPdfService
from tests.conftest import test_engine


def main() -> None:
    Base.metadata.create_all(bind=test_engine)
    connection = test_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, autoflush=False)()
    try:
        company = Empresa(
            codigo="preview-catalog",
            nombre="Aurora Moda SRL",
            nombre_marca="Aurora",
            eslogan="Prendas que acompañan tu estilo",
            color_primario="#243447",
            color_secundario="#FFF9EF",
            color_acento="#B46A3C",
            color_fondo="#F2EBDD",
            color_texto="#1B2735",
            active=True,
        )
        session.add(company)
        session.flush()
        owner = User(
            empresa_id=company.id,
            email="preview-catalog@example.com",
            name="Preview",
            hashed_password="preview-not-used",
            role="administrador",
            is_active=True,
        )
        category = Categoria(empresa_id=company.id, nombre="Polos")
        season = Temporada(empresa_id=company.id, nombre="Verano 2026")
        session.add_all([owner, category, season])
        session.flush()
        for index, (name, price) in enumerate((
            ("Polo Essential Navy", "89.90"),
            ("Polo Arena Premium", "109.50"),
            ("Polo Urbano Terracota", "119.00"),
            ("Polo Clásico Blanco", "79.90"),
            ("Polo Signature", "139.90"),
            ("Polo Casual Verde", "94.50"),
        ), start=1):
            session.add(Producto(
                codigo=f"AUR-{index:03d}",
                empresa_id=company.id,
                nombre=name,
                descripcion="Confección cómoda, acabado premium y diseño versátil para combinar durante toda la temporada.",
                precio=Decimal(price),
                categoria_id=category.id,
                temporada_id=season.id,
                active=True,
                visible_en_catalogo=True,
            ))
        session.flush()
        content, _ = CatalogPdfService(session, owner).generate(categoria_id=category.id)
        output = ROOT.parent / "output" / "pdf" / "catalogo-tenant-demo.pdf"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(content)
        print(output)
    finally:
        session.close()
        transaction.rollback()
        connection.close()


if __name__ == "__main__":
    main()
