# Guía de desarrollo

## Requisitos

- Git.
- Docker Engine y Docker Compose, o Docker Desktop.
- Python 3.12 si se ejecuta sin Docker.

## Preparar el repositorio

```bash
git clone https://github.com/rosellomateo/citypass-plus-analytics-backend.git
cd citypass-plus-analytics-backend
cp .env.example .env
```

Completar las variables de Azure siguiendo la [guía de configuración](configuration.md).

## Ejecutar con Docker

```bash
docker compose up --build
```

Los cambios dentro de `app/` reinician Uvicorn automáticamente. En usos
posteriores, si no cambiaron las dependencias ni el Dockerfile:

```bash
docker compose up
```

Para detener y retirar los recursos creados por este Compose:

```bash
docker compose down
```

Este comando afecta únicamente a los servicios definidos por este proyecto.

## Ejecutar sin Docker

Crear y activar un entorno virtual:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dev.txt
```

En Windows PowerShell, la activación es:

```powershell
.\.venv\Scripts\Activate.ps1
```

Iniciar el servidor cargando el `.env`:

```bash
uvicorn app.main:app --reload --env-file .env
```

## Estructura para una funcionalidad

Al incorporar un dominio analítico, mantener la separación actual:

1. contrato de salida en `app/schemas/`;
2. acceso al dataset mediante `app/repositories/` y `app/storage/`;
3. transformación o selección en `app/services/`;
4. ruta HTTP en `app/routers/`;
5. registro del router en `app/main.py`;
6. pruebas unitarias y de contrato en `test/`.

No cambiar rutas o campos existentes sin coordinar el cambio con los consumidores
de la API.

## Flujo de ramas

Crear las funcionalidades desde `develop` actualizado:

```bash
git switch develop
git pull origin develop
git switch -c feature/nombre-de-la-tarea
git push -u origin feature/nombre-de-la-tarea
```

Los pull requests de funcionalidad se abren contra `develop`. Antes de solicitar
revisión, ejecutar los controles indicados en [pruebas](testing.md).
