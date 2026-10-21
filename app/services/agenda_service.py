"""Reglas compartidas de agenda por bloques de sucursal."""
from datetime import date, datetime, time, timedelta


def hour_blocks(opening: time, closing: time) -> list[tuple[time, time]]:
    cursor = datetime.combine(date.today(), opening).replace(minute=0, second=0, microsecond=0)
    if cursor.time() < opening:
        cursor += timedelta(hours=1)
    end = datetime.combine(date.today(), closing)
    blocks: list[tuple[time, time]] = []
    while cursor + timedelta(hours=1) <= end:
        blocks.append((cursor.time(), (cursor + timedelta(hours=1)).time()))
        cursor += timedelta(hours=1)
    return blocks
