# CityPass+ Analytics Backend

API REST de analítica urbana de CityPass+. Expone con FastAPI los datos
agregados de la capa Gold almacenados como archivos Parquet en Azure Blob
Storage.

## Inicio rápido

Requisitos: Git y Docker con Docker Compose.

```bash
git clone https://github.com/rosellomateo/citypass-plus-analytics-backend.git
cd citypass-plus-analytics-backend
cp .env.example .env
docker compose up --build
```

En Windows PowerShell, usar `Copy-Item .env.example .env` para crear el archivo
de configuración. Antes de consultar las rutas de analítica, completar en
`.env` las credenciales de solo lectura de la capa Gold.

Servicios locales:

- API: <http://localhost:8000>
- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>
- Health check: <http://localhost:8000/health>

Verificación rápida:

```bash
curl http://localhost:8000/health
```

Respuesta esperada: `{"status":"ok"}`.

## Documentación

- [Arquitectura y flujo de datos](docs/architecture.md)
- [Configuración y variables de entorno](docs/configuration.md)
- [Referencia de la API](docs/api.md)
- [Guía de desarrollo](docs/development.md)
- [Pruebas y controles de calidad](docs/testing.md)
- [Despliegue y CI/CD](docs/deployment.md)

## Estado de seguridad

La API todavía **no implementa autenticación ni autorización por token**. CORS
limita qué navegadores pueden invocar la API desde una página web, pero no
protege los endpoints ni reemplaza la validación de identidad. Hasta incorporar
la capa de seguridad, no se debe considerar a estas rutas aptas para exponer
datos sensibles en Internet.

## Tecnologías principales

- Python 3.12
- FastAPI y Uvicorn
- Polars
- Azure Blob Storage
- Pytest y Ruff
- Docker y Docker Compose
