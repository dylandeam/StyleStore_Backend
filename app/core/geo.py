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


def calcular_distancia_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula la distancia de círculo máximo entre dos puntos geográficos
    usando la fórmula de Haversine (R = 6371 km).
    Retorna la distancia en kilómetros redondeada a 2 decimales.
    """
    # Convertir grados a radianes
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    # Fórmula de Haversine
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


def extraer_coordenadas_de_url(url: str | None) -> Tuple[float | None, float | None]:
    """
    Extrae latitud y longitud a partir de un enlace de Google Maps o Apple Maps.
    Soporta formatos:
    - /@-17.783321,-63.182134
    - ?q=-17.783321,-63.182134 o ll= o query=
    - Coordenadas numéricas libres en el texto
    """
    if not url:
        return None, None
    try:
        # Formato 1: /@-17.783321,-63.182134
        m1 = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", url)
        if m1:
            return float(m1.group(1)), float(m1.group(2))

        # Formato 2: ?q=-17.783321,-63.182134 o ll= o query=
        m2 = re.search(r"[?&](?:q|ll|query)=(-?\d+\.\d+),(-?\d+\.\d+)", url)
        if m2:
            return float(m2.group(1)), float(m2.group(2))

        # Formato 3: dos números decimales consecutivos tipo -17.xxxx, -63.xxxx
        m3 = re.search(r"(-?\d{1,2}\.\d{4,}),\s*(-?\d{1,3}\.\d{4,})", url)
        if m3:
            return float(m3.group(1)), float(m3.group(2))
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
    Retorna coordenadas aproximadas en Bolivia a partir de la ciudad o dirección.
    """
    txt = (direccion_o_ciudad or "").lower()
    for ciudad, coords in CIUDADES_BOLIVIA_COORDS.items():
        if ciudad in txt:
            return coords
    # Por defecto centro de Santa Cruz / Bolivia
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
