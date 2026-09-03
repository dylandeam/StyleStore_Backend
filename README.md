# StyleStore — Backend API

Backend RESTful para autenticación y gestión de usuarios desarrollado con **FastAPI**, **SQLAlchemy 2.0**, **PostgreSQL 18** y **Alembic**.

---

## 🚀 Características

- **Autenticación JWT:** Tokens de acceso (30 min) y refresh tokens (7 días).
- **Lista Negra de Tokens:** Invalidación de tokens en PostgreSQL al hacer logout.
- **Seguridad:** Hashing de contraseñas con `bcrypt` (cost factor 12).
- **ORM & Migraciones:** Modelos declarativos SQLAlchemy y migraciones automáticas con Alembic.
- **Validación Estricta:** Validación de datos en tiempo de ejecución con Pydantic v2.
- **Testing:** Suite completa de tests con `pytest` y base de datos aislada.

---

## 📦 Requisitos Previos

- Python 3.12+ / 3.13+
- PostgreSQL 16+ / 18+

---

## ⚙️ Instalación y Configuración

1. **Crear y activar entorno virtual:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. **Instalar dependencias:**
   ```powershell
   pip install -r requirements.txt
   ```

3. **Configurar variables de entorno:**
   Copia el archivo `.env.example` como `.env` y ajusta las credenciales:
   ```powershell
   cp .env.example .env
   ```

4. **Ejecutar migraciones:**
   ```powershell
   alembic upgrade head
   ```

5. **Iniciar el servidor:**
   ```powershell
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

---

## 📚 Documentación Interactiva

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Pruebas Automatizadas

```powershell
pytest -v
```
