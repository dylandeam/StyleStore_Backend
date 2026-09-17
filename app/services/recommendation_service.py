"""
Servicio de Recomendaciones Inteligentes (IA Local).
Analiza características de prendas (categoría, colección, temporada, precio y tokens semánticos)
para sugerir productos afines e incrementar el interés de compra del cliente.
"""
import re
from typing import List, Dict, Any
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from app.models.producto import Producto
from app.models.producto_color import ProductoColor
from app.models.stock_inventario import StockInventario


def _tokenize(text: str | None) -> set[str]:
    """Extrae palabras clave normalizadas (lematización/stopwords básicas en español)."""
    if not text:
        return set()
    words = re.findall(r"\b[a-záéíóúüñ]{3,}\b", text.lower())
    stopwords = {
        "para", "con", "las", "los", "del", "una", "uno", "por", "que", "este", "esta",
        "estilo", "ropa", "moda", "alta", "muy", "desde", "hasta", "como", "sobre", "color"
    }
    return {w for w in words if w not in stopwords}


class RecommendationService:
    """Motor local de recomendación de prendas basado en similitud multidimensional."""

    def __init__(self, db: Session):
        self.db = db

    def get_recommendations_for_product(
        self, codigo: str, limit: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Retorna los productos recomendados más similares al producto con el código dado.
        """
        clean_cod = codigo.strip().lower()
        target = (
            self.db.query(Producto)
            .options(
                joinedload(Producto.categoria),
                joinedload(Producto.coleccion),
                joinedload(Producto.temporada),
                joinedload(Producto.colores_rel).joinedload(ProductoColor.color),
            )
            .filter(func.lower(Producto.codigo) == clean_cod)
            .first()
        )
        if not target:
            return []

        candidates = (
            self.db.query(Producto)
            .options(
                joinedload(Producto.categoria),
                joinedload(Producto.coleccion),
                joinedload(Producto.temporada),
                joinedload(Producto.colores_rel).joinedload(ProductoColor.color),
            )
            .filter(
                Producto.active.is_(True),
                Producto.visible_en_catalogo.is_(True),
                Producto.codigo != target.codigo,
            )
            .all()
        )

        if not candidates:
            return []

        target_tokens = _tokenize(f"{target.nombre} {target.descripcion or ''}")
        target_price = float(target.precio)

        scored_candidates = []

        for p in candidates:
            score = 0.0
            reasons = []

            # 1. Misma categoría (peso 0.35)
            if target.categoria_id and p.categoria_id == target.categoria_id:
                score += 0.35
                cat_name = p.categoria.nombre if p.categoria else "Categoría similar"
                reasons.append(f"Misma categoría ({cat_name})")

            # 2. Misma colección (peso 0.25)
            if target.coleccion_id and p.coleccion_id == target.coleccion_id:
                score += 0.25
                col_name = p.coleccion.nombre if p.coleccion else "Colección afín"
                reasons.append(f"Colección {col_name}")

            # 3. Misma temporada (peso 0.20)
            if target.temporada_id and p.temporada_id == target.temporada_id:
                score += 0.20
                temp_name = p.temporada.nombre if p.temporada else "Temporada coincidente"
                reasons.append(f"Temporada {temp_name}")

            # 4. Rango de precio afín ±35% (peso 0.10)
            p_price = float(p.precio)
            if target_price > 0:
                price_ratio = min(p_price, target_price) / max(p_price, target_price)
                if price_ratio >= 0.65:
                    score += 0.10 * price_ratio
                    reasons.append("Precio similar")

            # 5. Similitud semántica de palabras clave (peso 0.10)
            p_tokens = _tokenize(f"{p.nombre} {p.descripcion or ''}")
            if target_tokens and p_tokens:
                intersection = target_tokens.intersection(p_tokens)
                union = target_tokens.union(p_tokens)
                jaccard = len(intersection) / len(union) if union else 0.0
                score += 0.10 * min(jaccard * 2, 1.0)
                if intersection:
                    reasons.append(f"Estilo: {', '.join(list(intersection)[:2])}")

            # 6. Colores afines
            target_colors = {pc.color.nombre.lower() for pc in target.colores_rel if pc.color}
            cand_colors = {pc.color.nombre.lower() for pc in p.colores_rel if pc.color}
            if target_colors and cand_colors and target_colors.intersection(cand_colors):
                score += 0.05
                reasons.append("Gama de colores afín")

            scored_candidates.append((score, reasons, p))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, reasons, p in scored_candidates[:limit]:
            results.append({
                "codigo": p.codigo,
                "nombre": p.nombre,
                "descripcion": p.descripcion,
                "foto": p.foto,
                "precio": float(p.precio),
                "categoria_nombre": p.categoria.nombre if p.categoria else None,
                "coleccion_nombre": p.coleccion.nombre if p.coleccion else None,
                "temporada_nombre": p.temporada.nombre if p.temporada else None,
                "score_afinidad": round(score, 2),
                "razon_recomendacion": " • ".join(reasons[:2]) if reasons else "Prenda sugerida para combinar tu estilo",
            })

        return results
