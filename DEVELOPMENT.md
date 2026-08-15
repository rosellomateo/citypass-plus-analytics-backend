# Desarrollo

## Ejecutar con Docker

Crear el archivo local de variables de entorno una sola vez:

```bash
cp .env.example .env
```

Construir la imagen e iniciar la API por primera vez:

```bash
docker compose up --build
```

En los siguientes usos alcanza con:

```bash
docker compose up
```

Abrir <http://localhost:8000/>. Los cambios dentro de `app/` reinician la API
automáticamente.

Ejecutar los controles de calidad dentro del contenedor de desarrollo:

```bash
docker compose run --rm api python -m ruff format --check .
docker compose run --rm api python -m ruff check .
docker compose run --rm api python -m pytest
```

Detener la API con `Ctrl+C` y retirar sus contenedores y red:

```bash
docker compose down
```

Volver a usar `docker compose up --build` después de modificar alguno de los archivos
de dependencias.

## Ejecutar sin Docker

Crear y activar un entorno virtual con Python 3.12. Después ejecutar:

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload
```
