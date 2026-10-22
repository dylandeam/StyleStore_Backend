# Evidencia REQ-042 a REQ-045 — ML reproducible

Fecha: 2026-10-21

## Dataset y reproducción

- Generador: `scripts/generate_ml_dataset.py`.
- Semilla fija: `20261021`.
- Salida versionada: `data/ml/ventas_sinteticas.csv` (730 registros diarios).
- SHA-256: `48CB4E8E85E4806C5736B4B4F4CEA2CBEE568A5B1E4385C437EFA5DFECB63A6E`.
- Variables: tendencia, mes, día de semana, fin de semana, promoción, transacciones e ingresos.

Comando reproducible:

```powershell
python scripts/generate_ml_dataset.py
```

## Modelo supervisado

- Regresión lineal con regularización ridge implementada en Python puro.
- Objetivo: ingresos diarios.
- División cronológica 80/20: 584 filas de entrenamiento y 146 de prueba.
- Resultado determinista: R² `0.8913`, MAE `Bs. 28.53`.
- El pronóstico de siete días se calibra con los últimos 30 días del tenant/sucursal, sin mezclar empresas.

## Modelo no supervisado

- K-means determinista, `k=3`, entrenado con 120 perfiles sintéticos RFM.
- Segmentos interpretables: ocasional, frecuente y alto valor.
- La asignación real usa frecuencia, valor monetario y recencia exclusivamente del tenant/sucursal autenticado.

## Integración y control

- `GET /api/v1/reportes/predicciones?sucursal_id=...` exige capacidades `reportes` y `predicciones`.
- Básico/Intermedio reciben bloqueo `403`; Profesional y Administrador SaaS pueden consultar según su ámbito.
- Dashboard Web muestra pronóstico, calidad del modelo, semilla y segmentos; si el plan no permite predicciones muestra la mejora requerida.
- Prueba A/B incluye una venta ajena de Bs. 9.999 y comprueba que no entra en la muestra del tenant autenticado.

## Validación

- Suite backend: 86 pruebas aprobadas.
- Angular producción: `main-F2OFZ3P3.js`.
- Pendiente para cerrar E2E: desplegar backend actualizado y guardar captura con un tenant Profesional.
