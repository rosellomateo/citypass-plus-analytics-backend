# CityPass+ Analytics Backend

API de analítica urbana para CityPass+, construida con FastAPI y Python 3.12.

## Inicio rápido con Docker

```bash
git clone https://github.com/rosellomateo/citypass-plus-analytics-backend.git
cd citypass-plus-analytics-backend
cp .env.example .env
docker compose up --build
```

En Windows PowerShell, reemplazar `cp .env.example .env` por:

```powershell
Copy-Item .env.example .env
```

La API queda disponible en <http://localhost:8000/> y su documentación
interactiva en <http://localhost:8000/docs>.

La guía completa para Linux, Windows, pruebas y trabajo en equipo está en
[DEVELOPMENT.md](DEVELOPMENT.md).
