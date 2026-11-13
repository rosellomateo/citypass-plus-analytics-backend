# Embed: autenticación de usuario por namespace

GET /embed/{modulo} recibe un único token de usuario en:

```http
Authorization: Bearer <access_token_human>
```

No se envía token de servicio ni X-Usuario-Token ni X-User-Token.
Se valida firma RS256 mediante JWKS_URL, JWT_ISSUER exacto, token_use=human,
ver=1 (entero), sub y jti no vacíos, iat y exp enteros válidos.
Se conserva la tolerancia de reloj de 60 segundos y el User-Agent del cliente JWKS.
En los cinco módulos de la tabla, aud debe ser un string con su propia audiencia.
citypass-admin-api ya no se acepta como alternativa.
GET /embed/identidad acepta citypass-admin-api como string o lista que lo incluya,
sin validar namespace, groups ni module. Mantiene firma, emisor, fechas y token human.
El namespace firmado del usuario determina a qué tablero puede acceder:

| Módulo en la URL | aud | namespace |
| --- | --- | --- |
| reclamos | citypass-reclamos-api | com.citypass.reclamos |
| residuos | citypass-residuos-api | com.citypass.residuos |
| movilidad | citypass-movilidad-api | com.citypass.movilidad |
| emergencias | citypass-emergencias-api | com.citypass.emergencias |
| espacios | citypass-espacios-api | com.citypass.espacios |

No se requieren ni se usan groups o module para autorizar embed.
El grupo admin no permite saltar la comprobación del namespace.
EDA y Analítica no tienen tablero embed.

Ejemplo: GET /embed/reclamos con el token human de Reclamos en Authorization.
Actualmente devuelve HTTP 200 y JSON {"status":"ok"}, con Cache-Control: private, no-store.
Esta etapa no genera HTML ni consulta Azure. No necesita EMBED_PLANTILLA.
La entrega de HTML con datos e informe sigue pendiente del build.

401: token ausente o inválido, incluyendo tipo o audiencia incorrectos.
403: namespace de otro módulo. 404: módulo desconocido.
503: configuración de seguridad ausente o JWKS inaccesible.

/analytics/* conserva token human, aud string igual a JWT_AUDIENCE (configurar
citypass-analitica-api) y pertenencia exacta al grupo admin. No exige grupos por
panel ni coincidencia del módulo con cada router. Los claims module y groups
conservan las validaciones estructurales del JWT humano.
Esta política es independiente de /embed/*.
