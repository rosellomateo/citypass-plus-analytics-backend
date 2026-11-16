# Configuración

La entrega HTML de `/embed/{modulo}` requiere una release del frontend en Blob y
las variables `EMBED_STORAGE_ACCOUNT_URL`, `EMBED_RELEASE_SHA` y, opcionalmente,
`EMBED_STORAGE_CONTAINER`, `EMBED_CACHE_TTL_SEGUNDOS` y
`EMBED_MANAGED_IDENTITY_CLIENT_ID`. Ver [Embed desde Blob](embed.md) para configurar
la identidad del backend, los permisos y la versión de la plantilla.

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

## Autenticación e indicadores adicionales

Las rutas `/analytics/*` validan JWT human por JWKS, emisor, audiencia configurada
y grupo `admin`. `/embed/*` conserva sus reglas por audiencia y namespace.

Los endpoints `/analytics/{area}/parte2` usan la conexión Gold existente; no
requieren nuevas variables obligatorias. Las fuentes, el contrato y las opciones
`PART2_EVENTS_BLOB` y `PART2_EVENTS_URL` se describen en [Parte 2](parte2.md).
