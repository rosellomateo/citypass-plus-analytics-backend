# Referencia de la API

Base local: `http://localhost:8000`.

Los contratos interactivos y ejemplos generados por FastAPI están disponibles en
`/docs`, `/redoc` y `/openapi.json`.

## Endpoints generales

| Método | Ruta | Descripción | Necesita Azure |
| --- | --- | --- | --- |
| `GET` | `/` | Comprobación básica; responde `{"message":"OK"}`. | No |
| `GET` | `/health` | Health check para Docker, pipeline y plataforma. | No |

El health check confirma que el proceso HTTP responde. No comprueba la conexión
con Storage ni la disponibilidad de los datasets Gold.

## Endpoints de analítica

Todos los endpoints actuales son `GET`, no reciben parámetros y conservan sus
rutas originales.

| Ruta | Respuesta | Fuente |
| --- | --- | --- |
| `/analytics/reclamos` | Lista de reclamos agregados | `Reclamos/reclamos_resumen.parquet` |
| `/analytics/seguridad-emergencias` | Lista de emergencias agregadas | `Emergencias y Seguridad/emergencias_resumen.parquet` |
| `/analytics/movilidad-urbana` | Lista de viajes agregados | `Movilidad Urbana/viajes_resumen.parquet` |
| `/analytics/espacios-cultura` | Lista de actividades agregadas | `Espacios Publicos y Cultura/actividades_resumen.parquet` |
| `/analytics/residuos` | Lista de alertas agregadas | `Gestion de Residuos Inteligente/alertas_resumen.parquet` |
| `/analytics/eventos` | Un evento temporal de prueba | Sin conexión a Gold |

### Reclamos

Cada elemento contiene:

`barrio`, `categoria`, `prioridad`, `origenClasificacion`, `estado_actual`,
`row_count`, `tiempo_prom_hasta_estado_actual`, `fecha_snapshot`.

### Seguridad y emergencias

Cada elemento contiene:

`estado_actual`, `prioridad`, `cantidadEmergencias`,
`tiempoPromRespuestaDespacho`, `tiempoPromRespuestaLugar`, `fecha_snapshot`.

### Movilidad urbana

Cada elemento contiene:

`fechaInicio`, `estacionInicio`, `duracionViaje`, `cantidadViajes`,
`duracionTotalViajes`, `promDuracion`, `fecha_snapshot`.

### Espacios públicos y cultura

La respuesta conserva `{datos, informe}`. Cada elemento de `datos` contiene:

`estado_actual`, `categoria`, `causaTipo`, `organizadorTipo`, `barrio`,
`cantidadActividades`, `cantidadMasivas`, `cantidadAfectadasPorClima`,
`totalVecesEventoClimatico`, `totalVecesReclamo`, `totalVecesIncidenteVial`,
`totalVecesAccidenteVial`, `fecha_snapshot` (fecha `YYYY-MM-DD`).

Cada fila es un agregado por estado, categoría, causa, organizador y barrio;
el total de actividades es la suma de `cantidadActividades`, no el número de filas.
Los contadores de incidentes y accidentes viales se mantienen separados.
`informe` sigue leyendo `espacios.json` del contenedor de análisis.

Este contrato reemplaza las reservas: no se publican cupos, inscriptos ni
porcentajes de ocupación porque no existen en el dataset de actividades.
El frontend web y la plantilla embed deben adaptarse a estos campos antes de
mostrar los indicadores de Cultura. `/embed/espacios` inyecta el mismo contrato;
la publicación de una plantilla en Blob no modifica su código al cambiar el backend.
Esta adaptación no incorpora `/analytics/culture/parte2`.

### Residuos

Cada elemento representa un agregado de alertas, no un contenedor individual:

`zona`, `tipoAlerta`, `prioridad`, `rangoNivelLlenado`, `cantidadAlertas`,
`cantidadResueltas`, `tiempoPromResolucion`, `fecha_snapshot`.

### Eventos

Devuelve un único objeto con:

`id_evento`, `tipo_evento`, `fecha_hora`, `area`, `version`, `id_correlacion`.

Este endpoint contiene datos estáticos de prueba y no debe interpretarse como un
feed de eventos productivo.

## Probar con curl o Postman

Ejemplo con curl:

```bash
curl --request GET \
  --url http://localhost:8000/analytics/residuos \
  --header 'Accept: application/json'
```

En Postman:

1. Crear una solicitud `GET`.
2. Usar, por ejemplo, `http://localhost:8000/analytics/residuos`.
3. Agregar `Accept: application/json` si no está presente.
4. Enviar la solicitud.

No se requiere token en el estado actual del proyecto.
