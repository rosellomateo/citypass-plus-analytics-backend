# Configuración

La aplicación usa variables de entorno. Para desarrollo local, copiar el archivo
de ejemplo y completar únicamente valores locales:

```bash
cp .env.example .env
```

El archivo `.env` está ignorado por Git. Nunca se deben guardar tokens SAS ni
otras credenciales en código, documentación, commits o capturas compartidas.

## Variables disponibles

| Variable | Requerida | Valor de ejemplo | Uso |
| --- | --- | --- | --- |
| `API_PORT` | No | `8000` | Puerto publicado por Docker Compose. No cambia el puerto interno del contenedor. |
| `CORS_ALLOWED_ORIGINS` | No | `http://localhost:5173` | Orígenes web permitidos, separados por comas. |
| `AZURE_STORAGE_ACCOUNT_URL` | Sí para analítica | `https://nombre-storage.blob.core.windows.net` | URL HTTPS de la cuenta de almacenamiento. |
| `AZURE_STORAGE_CONTAINER` | Sí para analítica | `gold` | Contenedor donde se encuentran los datasets Gold. |
| `AZURE_STORAGE_SAS_TOKEN` | Sí para analítica | Sin valor | SAS con permisos de lectura y listado. |

`/`, `/health`, `/docs`, `/redoc` y `/openapi.json` no necesitan acceder a
Azure. Las rutas `/analytics/*` sí necesitan las tres variables de Storage.

## CORS

Para permitir más de un frontend, separar los orígenes con comas y no incluir
rutas:

```dotenv
CORS_ALLOWED_ORIGINS=http://localhost:5173,https://frontend.example.com
```

La aplicación admite solicitudes `GET` y preflight `OPTIONS`, y los encabezados
`Accept` y `Content-Type`. El comodín `*` se rechaza deliberadamente.

El origen debe coincidir exactamente con el esquema, host y puerto del frontend.
Por ejemplo, `http://localhost:5173` y `http://localhost:4173` son orígenes
diferentes.

## Acceso a Azure Blob Storage

El SAS debe tener el alcance mínimo necesario:

- listado del contenedor;
- lectura de blobs;
- vigencia suficiente para el entorno donde se utilizará.

Si una variable falta o la URL no es HTTPS, la consulta de analítica falla con un
error de configuración. Si el SAS expiró o no tiene permisos, Azure rechazará la
operación.

## Seguridad pendiente

No hay middleware de autenticación, validación JWT ni autorización por roles.
Enviar un encabezado `Authorization` actualmente no modifica el comportamiento
de la API. La integración con el proveedor de identidad debe implementarse antes
de publicar datos sensibles.
