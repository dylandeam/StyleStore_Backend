"""
Utilidades geográficas y cálculo de distancias por Haversine (Punto 7 / v7).
Conforme a Especificación StyleStore v7.
Calcula la distancia real en km entre sucursales y destinos de clientes,
tiempo de entrega estimado y cotización dinámica de flete/delivery.
"""
import math
from decimal import Decimal
from typing import Tuple, Dict, Any

# Radio de la Tierra en kilómetros
EARTH_RADIUS_KM = 6371.0

# Coordenadas de referencia para ciudades principales de Bolivia (Lat, Lon)
CIUDADES_BOLIVIA_COORDS = {
    "la paz": (-16.5000, -68.1500),
    "el alto": (-16.5100, -68.1650),
    "santa cruz": (-17.7833, -63.1821),
    "cochabamba": (-17.3895, -66.1568),
    "sucre": (-19.0431, -65.2592),
    "tarija": (-21.5355, -64.7296),
    "oruro": (-17.9833, -67.1500),
    "potosi": (-19.5836, -65.7531),
    "potosí": (-19.5836, -65.7531),
    "trinidad": (-14.8333, -64.9000),
    "cobija": (-11.0267, -68.7692),
}

# Coordenadas de zonas, avenidas y anillos representativos en Santa Cruz, CBBA y LPZ
ZONAS_BOLIVIA_COORDS = {
    # Santa Cruz de la Sierra
    "alemana": (-17.7550, -63.1670),
    "av alemana": (-17.7550, -63.1670),
    "equipetrol": (-17.7680, -63.1950),
    "sirari": (-17.7650, -63.1990),
    "banzer": (-17.7500, -63.1780),
    "cristo redentor": (-17.7500, -63.1780),
    "monseñor rivero": (-17.7720, -63.1810),
    "el cristo": (-17.7720, -63.1810),
    "san martin": (-17.7690, -63.1910),
    "busch": (-17.7780, -63.1970),
    "mutualista": (-17.7650, -63.1550),
    "paragua": (-17.7580, -63.1600),
    "paraguá": (-17.7580, -63.1600),
    "villa 1ro de mayo": (-17.7950, -63.1350),
    "villa 1 de mayo": (-17.7950, -63.1350),
    "plan 3000": (-17.8300, -63.1380),
    "santos dumont": (-17.8100, -63.1880),
    "doble via": (-17.8150, -63.2100),
    "doble via la guardia": (-17.8150, -63.2100),
    "urubo": (-17.7600, -63.2200),
    "urubó": (-17.7600, -63.2200),
    "1er anillo": (-17.7810, -63.1810),
    "primer anillo": (-17.7810, -63.1810),
    "2do anillo": (-17.7760, -63.1770),
    "segundo anillo": (-17.7760, -63.1770),
    "3er anillo": (-17.7680, -63.1720),
    "tercer anillo": (-17.7680, -63.1720),
    "4to anillo": (-17.7580, -63.1680),
    "cuarto anillo": (-17.7580, -63.1680),
    "5to anillo": (-17.7490, -63.1640),
    "quinto anillo": (-17.7490, -63.1640),
    "6to anillo": (-17.7400, -63.1600),
    "sexto anillo": (-17.7400, -63.1600),
    "7mo anillo": (-17.7310, -63.1560),
    "septimo anillo": (-17.7310, -63.1560),
    "8vo anillo": (-17.7220, -63.1520),
    "octavo anillo": (-17.7220, -63.1520),
    "plaza 24 de septiembre": (-17.7833, -63.1821),
    "parque industrial": (-17.7580, -63.1350),

    # Cochabamba
    "av america": (-17.3750, -66.1550),
    "calacala": (-17.3720, -66.1600),
    "cala cala": (-17.3720, -66.1600),
    "recoleta": (-17.3780, -66.1490),
    "el prado": (-17.3850, -66.1580),
    "sacaba": (-17.4040, -66.0400),
    "quillacollo": (-17.3940, -66.2790),

    # La Paz
    "sopocachi": (-16.5120, -68.1300),
    "calacoto": (-16.5400, -68.0850),
    "san miguel": (-16.5420, -68.0820),
    "miraflores": (-16.5000, -68.1250),
    "san pedro": (-16.5050, -68.1390),
    "obrajes": (-16.5250, -68.1100),
    "achumani": (-16.5350, -68.0650),
}


def calcular_distancia_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula la distancia de círculo máximo entre dos puntos geográficos
    usando la fórmula de Haversine (R = 6371 km).
    Retorna la distancia en kilómetros redondeada a 2 decimales.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    distancia = EARTH_RADIUS_KM * c

    return round(distancia, 2)


def estimar_tiempo_entrega(distancia_km: float) -> int:
    """
    Estima el tiempo de entrega en minutos en base a tráfico urbano boliviano:
    - Preparación y despacho en tienda: 15 minutos base
    - Velocidad urbana promedio de motocicleta/repartidor: ~25 km/h (2.4 min por km)
    """
    minutos = 15 + int(distancia_km * 2.4)
    return max(20, minutos)


import re
import urllib.request


def _parse_coords_from_text(text: str) -> Tuple[float | None, float | None]:
    """Extrae coordenadas usando patrones de Google Maps y Apple Maps."""
    if not text:
        return None, None
    try:
        # Formato 1: /@-17.783321,-63.182134
        m1 = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", text)
        if m1:
            return float(m1.group(1)), float(m1.group(2))

        # Formato 2: ?q=-17.783321,-63.182134 o ll= o query= o daddr=
        m2 = re.search(r"[?&](?:q|ll|query|daddr|destination|saddr)=(-?\d+\.\d+),(-?\d+\.\d+)", text)
        if m2:
            return float(m2.group(1)), float(m2.group(2))

        # Formato 3: /place/(-17.xxxx)[,+](-63.xxxx)
        m3 = re.search(r"/place/(-?\d+\.\d+)[,+](-?\d+\.\d+)", text)
        if m3:
            return float(m3.group(1)), float(m3.group(2))

        # Formato 4: dos números decimales consecutivos tipo -17.xxxx, -63.xxxx
        m4 = re.search(r"(-?\d{1,2}\.\d{3,}),\s*(-?\d{1,3}\.\d{3,})", text)
        if m4:
            return float(m4.group(1)), float(m4.group(2))
    except Exception:
        pass
    return None, None


def extraer_coordenadas_de_url(url: str | None) -> Tuple[float | None, float | None]:
    """
    Extrae latitud y longitud a partir de un enlace de Google Maps o Apple Maps.
    Soporta URLs directas y enlaces cortos con redirección (maps.app.goo.gl, goo.gl/maps).
    """
    if not url:
        return None, None
    url_clean = url.strip()

    # 1. Intentar extracción directa
    lat, lon = _parse_coords_from_text(url_clean)
    if lat is not None and lon is not None:
        return lat, lon

    # 2. Si es enlace de Google Maps (incluyendo acortados como maps.app.goo.gl o goo.gl), resolver redirect
    if any(k in url_clean.lower() for k in ["maps.app.goo.gl", "goo.gl/maps", "google.com/maps", "maps.google"]):
        try:
            req = urllib.request.Request(
                url_clean,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                final_url = resp.geturl()
                lat_f, lon_f = _parse_coords_from_text(final_url)
                if lat_f is not None and lon_f is not None:
                    return lat_f, lon_f

                # Si no está en la URL final, buscar en el HTML inicial
                html_snippet = resp.read(4096).decode("utf-8", errors="ignore")
                lat_h, lon_h = _parse_coords_from_text(html_snippet)
                if lat_h is not None and lon_h is not None:
                    return lat_h, lon_h
        except Exception:
            pass

    return None, None


def cotizar_costo_envio(distancia_km: float) -> Decimal:
    """
    Tarifa oficial Delivery StyleStore (Servicio Privado):
    - Tarifa fija base: Bs. 5.00
    - A partir de los 5 Bs, se le va sumando 0.60 Bs (60 centavos) por cada kilómetro recorrido.
    Fórmula: 5.00 + (distancia_km * 0.60)
    """
    d = max(0.0, float(distancia_km or 0.0))
    costo = 5.00 + (d * 0.60)
    return Decimal(str(round(costo, 2)))


def geocodificar_aproximado(direccion_o_ciudad: str) -> Tuple[float, float]:
    """
    Retorna coordenadas aproximadas en Bolivia a partir de la ciudad, avenida, barrio o zona.
    Prioriza zonas específicas sobre centros de ciudad generales.
    """
    txt = (direccion_o_ciudad or "").lower()

    # 1. Zonas, anillos y avenidas específicas
    for zona, coords in ZONAS_BOLIVIA_COORDS.items():
        if zona in txt:
            return coords

    # 2. Ciudades principales
    for ciudad, coords in CIUDADES_BOLIVIA_COORDS.items():
        if ciudad in txt:
            return coords

    # Por defecto centro de Santa Cruz
    return (-17.7833, -63.1821)


def calcular_cotizacion_completa(
    origen_lat: float,
    origen_lon: float,
    destino_lat: float,
    destino_lon: float,
) -> Dict[str, Any]:
    """
    Calcula distancia, tiempo y costo consolidado entre dos puntos.
    """
    distancia = calcular_distancia_haversine(origen_lat, origen_lon, destino_lat, destino_lon)
    # Si la distancia calculada es casi cero (ambos puntos cayeron en la misma coordenada genérica)
    if distancia < 0.2:
        distancia = 3.20  # Distancia estimada urbana razonable de despacho en lugar de 0

    minutos = estimar_tiempo_entrega(distancia)
    costo = cotizar_costo_envio(distancia)

    return {
        "distancia_km": distancia,
        "minutos_estimados": minutos,
        "costo_envio": float(costo),
        "costo": float(costo),
        "tarifa_base": 5.00,
        "costo_por_km": 0.60,
        "moneda": "BOB",
        "origen": {"lat": origen_lat, "lon": origen_lon},
        "destino": {"lat": destino_lat, "lon": destino_lon},
    }
