# Desarrollo

## Requisitos

- Git.
- [Docker Engine](https://docs.docker.com/engine/install/) con el
  [plugin de Docker Compose](https://docs.docker.com/compose/install/linux/) en Linux.
- [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/)
  en Windows.

Comprobar la instalación:

```bash
docker --version
docker compose version
```

En Windows se recomienda Docker Desktop con el backend WSL 2. En Linux se debe
instalar Docker Engine y el plugin de Docker Compose.

## Descargar el proyecto

```bash
git clone https://github.com/rosellomateo/citypass-plus-analytics-backend.git
cd citypass-plus-analytics-backend
git switch develop
git pull origin develop
```

## Ejecutar con Docker en Linux

Crear el archivo local de variables de entorno una sola vez:

```bash
cp .env.example .env
```

Construir la imagen e iniciar la API:

```bash
docker compose up --build
```

## Ejecutar con Docker en Windows

Abrir PowerShell dentro de la carpeta del proyecto y crear el archivo local de
variables de entorno:

```powershell
Copy-Item .env.example .env
```

Construir la imagen e iniciar la API:

```powershell
docker compose up --build
```

Los comandos restantes de Docker son iguales en Linux y Windows.

## Uso diario

En los siguientes usos, mientras no cambien las dependencias, alcanza con:

```bash
docker compose up
```

Direcciones disponibles:

- API: <http://localhost:8000/>
- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

Los cambios dentro de `app/` reinician la API automáticamente.

Detener la API con `Ctrl+C` y retirar sus contenedores y red:

```bash
docker compose down
```

Volver a ejecutar `docker compose up --build` después de modificar
`requirements.txt`, `requirements-dev.txt` o el `Dockerfile`.

## Controles de calidad

Ejecutar los controles de calidad dentro del contenedor de desarrollo:

```bash
docker compose run --rm api python -m ruff format --check .
docker compose run --rm api python -m ruff check .
docker compose run --rm api python -m pytest
```

Los tres controles deben finalizar correctamente antes de abrir un pull request.

## Trabajo con ramas

Crear cada rama de funcionalidad desde un `develop` actualizado:

```bash
git switch develop
git pull origin develop
git switch -c feature/nombre-de-la-tarea
git push -u origin feature/nombre-de-la-tarea
```

Los pull requests se abren contra `develop` y deben ser revisados por el otro
integrante del equipo.

## Ejecutar sin Docker

Se requiere Python 3.12. Crear el entorno virtual:

```bash
python -m venv .venv
```

Activarlo en Linux:

```bash
source .venv/bin/activate
```

O activarlo en Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instalar las dependencias y ejecutar la API:

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload
```

## Variables de entorno

`.env.example` contiene los nombres de las variables necesarias. Cada integrante
debe copiarlo como `.env` y completar solamente valores locales. El archivo `.env`
no se sube al repositorio y nunca debe contener credenciales compartidas por Git.
