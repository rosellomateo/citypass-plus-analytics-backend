# Analítica de Identidad

GET /analytics/identidad devuelve datos e informe, como los demás módulos.
Requiere Authorization: Bearer <token human>, audiencia de Analítica configurada
con JWT_AUDIENCE y grupo admin. Utiliza los repositorios compartidos de Azure.

Ubicaciones asumidas, pendientes de confirmar con el productor:
- Parquet en el contenedor de datos: LDAP/autenticacion_resumen.parquet.
- Informe en el contenedor de informes: identidad.json.

El informe usa InformeAnalisis, incluyendo resumen ejecutivo, puntos destacados,
recomendaciones y riesgos. Si identidad.json no existe, se devuelve informe: null; otros errores no se ocultan.

Las filas conservan department, username, event_type (strings), cantidadEventos
(entero de 64 bits en el parquet) y fecha_snapshot (fecha YYYY-MM-DD).
Las cinco columnas son obligatorias y admiten null, como los otros esquemas.
No se agregan ni se filtran filas: el parquet ya contiene el resumen.

GET /embed/identidad exige token human con aud citypass-admin-api, como string o
lista que lo incluya. No exige namespace, groups ni module. Mantiene firma JWKS,
emisor, fechas, ver, sub y jti. Devuelve HTML con los datos del mismo servicio,
incluyendo `informe: null` si todavía no existe `identidad.json`.

Requiere una release del frontend que declare `identidad` en su manifiesto y el
SHA correspondiente en `EMBED_RELEASE_SHA`. Con una release anterior de cinco
módulos, responde 503; los tableros existentes conservan su funcionamiento.
