# Pruebas y controles de calidad

## Suite local

Con el entorno virtual activo:

```bash
python -m ruff format --check .
python -m ruff check .
python -m pytest
```

La configuración de Pytest exige una cobertura mínima total del 60 % y genera un
reporte en la terminal.

Los mismos controles se pueden ejecutar en contenedores:

```bash
docker compose run --rm api python -m ruff format --check .
docker compose run --rm api python -m ruff check .
docker compose run --rm api python -m pytest
```

## Tipos de pruebas

| Ubicación | Alcance |
| --- | --- |
| `test/test_main.py` | Aplicación, health check y política CORS. |
| `test/unit/` | Configuración, Storage, repositorio, esquemas y routers. |
| `test/integration/` | Conexión y lectura real de Azure Gold. |

Las pruebas de routers reemplazan el repositorio mediante inyección de
dependencias; por eso la suite normal no necesita credenciales de Azure.

## Prueba real contra Gold

La prueba marcada como `azure` está deshabilitada por defecto. Con un `.env`
válido, se puede ejecutar dentro de Docker:

```bash
docker compose build api
docker compose run --rm -e RUN_AZURE_INTEGRATION_TESTS=true api \
  python -m pytest -m azure --no-cov
```

Esta prueba usa recursos reales y debe ejecutarse con credenciales de solo
lectura. No imprimir ni copiar el SAS en los logs.

## Smoke test manual

Con la API iniciada:

```bash
curl --fail http://localhost:8000/health
curl --fail http://localhost:8000/analytics/reclamos
```

El primer comando prueba el proceso; el segundo también prueba la configuración,
la conexión a Azure y el contrato del dataset de reclamos.
