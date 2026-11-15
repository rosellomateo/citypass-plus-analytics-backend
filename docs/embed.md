# Entrega de tableros HTML desde Azure Blob

`GET /embed/{modulo}` valida el JWT del usuario, carga una plantilla versionada del
frontend desde un contenedor privado, inyecta la respuesta de analítica y devuelve
un HTML autocontenido. El navegador del módulo utiliza su sesión existente.

## Autenticación existente

El backend del equipo llama por HTTPS con un único token de usuario:

```http
GET /embed/reclamos
Authorization: Bearer <access_token_human>
```

Se conserva la política actual de `develop`: firma RS256 mediante `JWKS_URL`,
`JWT_ISSUER` exacto, `token_use=human`, `ver=1` entero, `sub` y `jti` no vacíos,
`iat` y `exp` enteros válidos y tolerancia de reloj de 60 segundos. En estos cinco
módulos, `aud` debe ser un string con la audiencia exacta de la tabla.

| Módulo | aud | namespace |
| --- | --- | --- |
| reclamos | citypass-reclamos-api | com.citypass.reclamos |
| residuos | citypass-residuos-api | com.citypass.residuos |
| movilidad | citypass-movilidad-api | com.citypass.movilidad |
| emergencias | citypass-emergencias-api | com.citypass.emergencias |
| espacios | citypass-espacios-api | com.citypass.espacios |

El namespace firmado autoriza el módulo; `groups` y `module` no participan de esta
política. El grupo `admin` no permite saltar audiencia o namespace. No se requiere
token de servicio, `X-Usuario-Token` ni `X-User-Token`. La validación se ejecuta en
cada request, incluso si el HTML está cacheado. No se añade introspección remota:
los cambios de permisos están sujetos a la vigencia del JWT.

La propuesta inicial del workspace usaba dos tokens; esta integración sigue el
contrato más reciente de autenticación ya implementado en este repositorio.
`/analytics/*` conserva su propia política de JWT de Analítica y grupo `admin`.

## Configuración de Azure y del backend

El pipeline del frontend publica en `citypassstorage`:

```text
plantillas/releases/<sha-completo-del-frontend>/embed.html
plantillas/releases/<sha-completo-del-frontend>/manifest.json
plantillas/releases/<sha-completo-del-frontend>/SHA256SUMS
```

Configurar en las Application Settings de la Web App del **backend**:

| Variable | Valor |
| --- | --- |
| `EMBED_STORAGE_ACCOUNT_URL` | `https://citypassstorage.blob.core.windows.net` |
| `EMBED_STORAGE_CONTAINER` | `plantillas` (predeterminado) |
| `EMBED_RELEASE_SHA` | SHA de 40 caracteres del commit del **frontend** publicado |
| `EMBED_CACHE_TTL_SEGUNDOS` | `600` (predeterminado); `0` desactiva la caché de HTML |
| `EMBED_MANAGED_IDENTITY_CLIENT_ID` | Opcional: Client ID de una identidad asignada por el usuario al backend |

No usar el SHA del backend ni un tag o alias `latest` en `EMBED_RELEASE_SHA`.
Seleccionar explícitamente la release permite controlar su activación y el rollback.

1. En la Web App del backend, habilitar **Identity → System assigned**. Si se usa
   una identidad asignada por el usuario, adjuntarla a la Web App y configurar su
   Client ID en la variable opcional de arriba.
2. En `citypassstorage → Containers → plantillas → Access control (IAM)`, asignar
   **Storage Blob Data Reader** a la identidad del backend, limitado al contenedor.
   La identidad OIDC de GitHub es independiente: su configuración no otorga acceso
   automáticamente al proceso de la Web App.
3. Mantener el contenedor privado y permitir que la red del backend alcance Blob.
4. Configurar estas variables y reiniciar el backend al cambiar de release. La
   descarga usa `DefaultAzureCredential`, sin SAS ni claves de cuenta para la
   plantilla. En desarrollo local puede usar la sesión de `az login`.
5. Conservar `AZURE_STORAGE_*` y `AZURE_ANALISIS_*` para leer Gold e informes.
   Esos conectores mantienen su autenticación SAS existente.

La configuración y descarga ocurren en el primer request autorizado de HTML,
no al importar la aplicación. `/health` funciona sin una release configurada.
Antes de que se publique/configure una release, la entrega devuelve `503`.

## Integridad, caché e inyección

Se requieren los tres archivos. Se descarga primero `SHA256SUMS`, que el pipeline
publica al final. Se verifican los hashes del manifiesto y del HTML, el commit,
tamaño, versión del manifiesto y módulos. El HTML debe conservar una aparición de
cada marcador `__CITYPASS_MODULO__` y `__CITYPASS_DATOS__`. La descarga del HTML está
limitada a 5 MiB; manifiesto y checksums también tienen límites de tamaño.

La plantilla se conserva en memoria hasta reiniciar el proceso porque corresponde
a una release inmutable. El HTML con datos tiene TTL por módulo y por proceso.
Un lock evita descargas simultáneas al llenar la caché. Al vencer el TTL se leen
Gold e informes nuevamente, reutilizando la plantilla. No se sirven resultados
vencidos si esa lectura falla.

Se reutilizan los cinco servicios actuales; el payload es exactamente su
`model_dump(mode="json")`: `{"datos": [...], "informe": {...}}`. La serialización
escapa `<` como `\u003c` para que un valor con `</script>` no cierre el bloque JSON.
Los tokens no se insertan en el HTML.

El contenido cacheado depende solo del módulo. Si se incorporan filtros o datos
particulares por usuario, hay que adaptar la clave de caché antes de habilitarlos.

## Respuesta e integración de otros equipos

Para los cinco módulos, la respuesta es `200 text/html; charset=utf-8` con:

```http
Cache-Control: private, no-store
Content-Security-Policy: default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: https:; font-src data:
X-Content-Type-Options: nosniff
Referrer-Policy: no-referrer
```

Cada equipo debe identificar la sesión del usuario, reenviar su access token a
Analítica y servir el HTML sin modificarlo ni cachearlo. Reenviar también las
cinco cabeceras anteriores, incluyendo `Content-Type`.

En su frontend:

```html
<iframe src="/admin/analitica" title="Analítica" sandbox="allow-scripts"
        style="width:100%;height:1200px;border:0"></iframe>
```

La ruta `/admin/analitica` pertenece al backend del equipo. Ese backend llama a
Analítica; una carga normal de iframe no permite agregar el Bearer en `src`.
El HTML embebido debe renderizar el tablero sin pasar por la pantalla de login.

## Compatibilidad con Identidad

La release actual del frontend solo define cinco módulos. `/embed/identidad`
conserva la prueba autenticada `200 application/json` con `{"status":"ok"}`, sin
cargar la plantilla ni los datos. Acepta `citypass-admin-api` como string o lista
que la incluya y mantiene sus validaciones, sin exigir namespace/grupos.
Para entregar HTML de Identidad hace falta ampliar el paquete en ambos repositorios.

## Errores y verificación

| Código | Motivo |
| --- | --- |
| 401 | Token ausente, inválido o expirado, incluido tipo/audiencia incorrectos |
| 403 | Namespace de otro módulo |
| 404 | Módulo desconocido |
| 503 | Falta configuración, JWKS inaccesible, release ausente/incompleta/corrupta, falta de permisos de Blob o datos/informe no disponibles |

Las respuestas de error de entrega no exponen datos ni detalles de credenciales.
Se registran accesos por módulo y usuario, sin tokens.

Verificación manual con un JWT válido del módulo:

```bash
curl --fail --show-error --dump-header /tmp/embed-headers.txt \
  -H "Authorization: Bearer ${TOKEN_USUARIO}" \
  "https://<backend>/embed/reclamos" --output /tmp/embed-reclamos.html
```

El HTML contiene datos del módulo; conservarlo en un lugar privado. Comprobar
también el rechazo sin token, con un token de otro módulo y que `/health` responda.
La suite automatizada usa RSA y Blob/repositorios simulados, sin credenciales ni
dependencias de red. Una prueba real requiere primero publicar el paquete del
frontend y otorgar permisos a la identidad de la Web App.
