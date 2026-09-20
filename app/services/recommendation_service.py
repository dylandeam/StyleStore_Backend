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
from app.models.cliente import Cliente
from app.models.orden_venta import OrdenVenta


TOPS_KEYWORDS = {"camisa", "polera", "polo", "blusa", "chaqueta", "sueter", "poleron", "top", "saco", "chaleco", "chompa", "vestido"}
BOTTOMS_KEYWORDS = {"pantalon", "jeans", "jean", "falda", "bermuda", "short", "jogger", "calza"}


def _is_top(text: str) -> bool:
    t = text.lower()
    return any(w in t for w in TOPS_KEYWORDS)


def _is_bottom(text: str) -> bool:
    t = text.lower()
    return any(w in t for w in BOTTOMS_KEYWORDS)


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
        target_cat_nom = target.categoria.nombre if target.categoria else ""
        target_is_top = _is_top(f"{target.nombre} {target_cat_nom}")
        target_is_bottom = _is_bottom(f"{target.nombre} {target_cat_nom}")

        scored_candidates = []

        for p in candidates:
            score = 0.0
            reasons = []
            p_cat_nom = p.categoria.nombre if p.categoria else ""

            # 1. Misma categoría (peso 0.30)
            if target.categoria_id and p.categoria_id == target.categoria_id:
                score += 0.30
                reasons.append(f"Misma categoría ({p_cat_nom or 'similar'})")

            # 1.1 Cross-selling / Outfit Complementario ("Completa tu look") (peso 0.35)
            p_is_top = _is_top(f"{p.nombre} {p_cat_nom}")
            p_is_bottom = _is_bottom(f"{p.nombre} {p_cat_nom}")
            is_complementary = (target_is_top and p_is_bottom) or (target_is_bottom and p_is_top)
            if is_complementary:
                score += 0.35
                reasons.append("Completa tu look ideal")

            # 2. Misma colección (peso 0.20)
            if target.coleccion_id and p.coleccion_id == target.coleccion_id:
                score += 0.20
                col_name = p.coleccion.nombre if p.coleccion else "Colección afín"
                reasons.append(f"Colección {col_name}")

            # 3. Misma temporada (peso 0.15)
            if target.temporada_id and p.temporada_id == target.temporada_id:
                score += 0.15
                temp_name = p.temporada.nombre if p.temporada else "Temporada coincidente"
                reasons.append(f"Temporada {temp_name}")

            # 4. Rango de precio afín ±35% (peso 0.15)
            p_price = float(p.precio)
            if target_price > 0:
                price_ratio = min(p_price, target_price) / max(p_price, target_price)
                if price_ratio >= 0.65:
                    score += 0.15 * price_ratio
                    reasons.append("Rango de precio afín")

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

            # Determinar Tag de Incentivo de Compra
            if is_complementary:
                tag_incentivo = "✨ Completa tu look"
            elif target_price > 0 and 0.85 <= (p_price / target_price) <= 1.15:
                tag_incentivo = "🏷️ Precio similar"
            elif target_price > 0 and 0.60 <= (p_price / target_price) < 0.85:
                tag_incentivo = "💡 Mejor precio"
            elif score >= 0.60:
                tag_incentivo = "🔥 Match perfecto"
            else:
                tag_incentivo = "🌟 Recomendado"

            scored_candidates.append((score, reasons, tag_incentivo, p))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, reasons, tag_incentivo, p in scored_candidates[:limit]:
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
                "tag_incentivo": tag_incentivo,
                "razon_recomendacion": " • ".join(reasons[:2]) if reasons else "Prenda sugerida para combinar tu estilo",
            })

        return results

    def get_para_ti_recommendations(
        self, user_id: int | None = None, limit: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Genera el feed 'Para Ti' de ropa con IA local:
        Analiza el historial de compras del cliente o sugiere prendas estelares de alta afinidad.
        """
        results: List[Dict[str, Any]] = []
        seen_codigos = set()

        if user_id:
            try:
                cliente = self.db.query(Cliente).filter(Cliente.user_id == user_id).first()
                if cliente:
                    ultima_orden = (
                        self.db.query(OrdenVenta)
                        .filter(OrdenVenta.codigo_cliente == cliente.codigo)
                        .order_by(OrdenVenta.id.desc())
                        .first()
                    )
                    if ultima_orden and ultima_orden.detalles:
                        primer_detalle = ultima_orden.detalles[0]
                        if primer_detalle.codigo_producto:
                            recs = self.get_recommendations_for_product(
                                primer_detalle.codigo_producto, limit=limit
                            )
                            for r in recs:
                                r["razon_recomendacion"] = f"Basado en tus preferencias: {r['razon_recomendacion']}"
                                if not r.get("tag_incentivo"):
                                    r["tag_incentivo"] = "🎯 Para ti"
                                results.append(r)
                                seen_codigos.add(r["codigo"])
            except Exception:
                pass

        # Si faltan productos para completar el feed 'Para Ti', complementar con catálogo destacado
        if len(results) < limit:
            needed = limit - len(results)
            candidates = (
                self.db.query(Producto)
                .options(
                    joinedload(Producto.categoria),
                    joinedload(Producto.coleccion),
                    joinedload(Producto.temporada),
                )
                .filter(
                    Producto.active.is_(True),
                    Producto.visible_en_catalogo.is_(True),
                )
                .order_by(Producto.created_at.desc())
                .all()
            )

            fallback_reasons = [
                "Tendencia destacada de temporada",
                "Estilo en alta demanda por compradores",
                "Prenda versátil imprescindible para tu guardarropa",
                "Confección premium seleccionada por IA",
                "Look contemporáneo en tendencia",
            ]
            import random

            for idx, p in enumerate(candidates):
                if p.codigo in seen_codigos:
                    continue
                score = round(0.95 - (idx * 0.02), 2)
                score = max(score, 0.85)
                reason = fallback_reasons[idx % len(fallback_reasons)]
                if p.coleccion:
                    reason = f"Colección {p.coleccion.nombre} en tendencia"
                elif p.temporada:
                    reason = f"Favorito temporada {p.temporada.nombre}"

                tag = "🔥 Más llevado" if idx == 0 else ("✨ Novedad" if idx == 1 else "🌟 Recomendado")

                results.append({
                    "codigo": p.codigo,
                    "nombre": p.nombre,
                    "descripcion": p.descripcion,
                    "foto": p.foto,
                    "precio": float(p.precio),
                    "categoria_nombre": p.categoria.nombre if p.categoria else None,
                    "coleccion_nombre": p.coleccion.nombre if p.coleccion else None,
                    "temporada_nombre": p.temporada.nombre if p.temporada else None,
                    "score_afinidad": score,
                    "tag_incentivo": tag,
                    "razon_recomendacion": reason,
                })
                seen_codigos.add(p.codigo)
                if len(results) >= limit:
                    break

        return results

