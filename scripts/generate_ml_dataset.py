"""Regenera de forma determinista el CSV usado para documentar los modelos ML."""
import csv
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.ml_service import generate_synthetic_sales


def main() -> None:
    destination = Path(__file__).resolve().parents[1] / "data" / "ml" / "ventas_sinteticas.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = generate_synthetic_sales()
    with destination.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} filas generadas en {destination}")


if __name__ == "__main__":
    main()
