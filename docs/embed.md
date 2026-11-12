# Embed: etapa de validación de servicios

GET /embed/{modulo} devuelve 200 {"status":"ok"} después de autorizar el servicio.
Esta etapa no genera HTML ni consulta Azure. No necesita EMBED_PLANTILLA.

Enviar Authorization: Bearer <token de servicio>. No se requiere X-Usuario-Token.
Se exige firma RS256 válida mediante JWKS_URL, JWT_ISSUER exacto, token_use=service,
ver=1 (entero), aud como lista que incluya citypass, sub y jti no vacíos,
iat y exp enteros válidos y namespace exacto correspondiente al tablero.
Se conserva la tolerancia de reloj de 60 segundos y el User-Agent del cliente JWKS.

Namespaces:
- reclamos: com.citypass.reclamos
- residuos: com.citypass.residuos
- movilidad: com.citypass.movilidad
- emergencias: com.citypass.emergencias
- espacios: com.citypass.espacios

No se exige groups ni module al servicio. El backend solicitante es responsable de
controlar el acceso de sus usuarios; Analytics autentica al servicio en esta etapa.
No se usa EMBED_SERVICE_NAMESPACES ni EMBED_SERVICE_AUDIENCE: los valores se fijan
según la tabla y el modelo de token acordados. EDA y Analítica no tienen tablero embed.

/analytics/* exige token human, aud string igual a JWT_AUDIENCE (configurar
citypass-analitica-api) y pertenencia exacta al grupo admin. No exige grupos por
panel ni coincidencia del módulo con cada router. Los claims module y groups
conservan las validaciones estructurales del JWT humano.
permissions.py contiene solo la política admin; dependencies.py valida el token
y aplica requerir_admin. Esta política no se usa en /embed/*.


401: token ausente o inválido. 403: namespace de otro módulo. 404: módulo desconocido.
503: configuración de seguridad ausente o JWKS inaccesible.
Para probar con Identidad, obtener un token service nuevo; el payload de ejemplo
no es un token firmado y sus fechas no deben reutilizarse.
La entrega de HTML con datos e informe se retomará cuando esté disponible el build.
