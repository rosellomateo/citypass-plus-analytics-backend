# Indicadores adicionales de la parte 2

La web de Analítica consulta `GET /analytics/{area}/parte2`. El router se registra
en la aplicación y mantiene la política de los otros endpoints `/analytics/*`:
JWT human con la audiencia de Analítica configurada y grupo `admin`.
No cambia la autenticación de `/embed/*`.

| Área | Ruta | JSON en el contenedor Gold |
| --- | --- | --- |
| Reclamos | `/analytics/claims/parte2` | `parte2/claims.json` |
| Emergencias | `/analytics/emergencies/parte2` | `parte2/emergencies.json` |
| Movilidad | `/analytics/mobility/parte2` | `parte2/mobility.json` |
| Cultura | `/analytics/culture/parte2` | `parte2/culture.json` |
| Residuos | `/analytics/waste/parte2` | `parte2/waste.json` |
| EDA | `/analytics/eda/parte2` | `parte2/eda.json` |

## Fuente y contrato

Se utiliza la conexión existente `AZURE_STORAGE_*`, cuyo contenedor corresponde
a Gold. Los JSON de parte 2 no se leen desde el contenedor de informes de IA.
Ejemplo de estructura, con un valor ilustrativo:

```json
{
  "fecha_snapshot": "2026-11-16",
  "datos": [
    {"id": "c1", "etiqueta": "Indicador publicado", "valor": 7, "unidad": "estaciones"}
  ]
}
```

Los cinco tableros usan `c1` a `c6`; Emergencias también admite `c4b` y `c5b`.
EDA usa `received`, `delivered`, `pending` y `critical`, con `etiqueta` obligatoria.
Cada indicador puede incluir `detalle: [{"etiqueta": "Desglose", "valor": 2}]`.
Los números deben ser finitos y los identificadores únicos. `informe` es opcional
y sigue el esquema `InformeAnalisis`.

Los agregados de Cultura deben declarar `"version_cultura": 2`. Los agregados
anteriores no se muestran como indicadores actuales de actividades.

Si el JSON falta con `BlobNotFound`, se pueden derivar algunos indicadores de
Reclamos y Emergencias desde sus resúmenes Gold, cuando incluyen las columnas
necesarias. No se derivan afectaciones de estaciones a partir del total de viajes:
Movilidad necesita su propio corte `parte2/mobility.json`.

Sin una fuente disponible se responde `200` con `datos: []`, no con métricas
inventadas ni ceros por falta de información. La publicación de los cortes
corresponde al productor de datos. Un error de permisos, configuración, formato
o conexión no equivale a un dataset vacío y devuelve `503`.

## Caso 2: reclamos que afectaron a otros módulos

Si falta `parte2/claims.json`, el backend calcula `c2` desde
`Reclamos/reclamos_resumen.parquet`: suma `row_count` donde
`afectaOtrosModulos = true`, usando únicamente el último `fecha_snapshot`.
La bandera la calcula el productor Gold a partir de las referencias de otros
módulos. Un reclamo cuenta una vez aunque esté relacionado con varios módulos.

Este cálculo es independiente de `causaTipo`: un reclamo ciudadano sin causa
externa puede afectar a otros módulos. Si faltan las columnas o contienen datos
desconocidos, `c2` no se publica. Una bandera booleana completa sin reclamos
afectados sí produce un cero real. El JSON publicado conserva su prioridad;
no se mezclan cortes de fuentes diferentes.

La tarjeta «Reclamos que afectaron a otros módulos» y su barra en «Reclamos
vinculados a otros servicios» ya existen en el frontend. El mismo indicador
se incorpora al bloque `parte2` del HTML embed. No identifica exclusivamente
ciclovías, porque esa dimensión no está en el resumen Gold actual.

## Corte opcional de eventos

Cultura, Emergencias y EDA pueden complementar sus indicadores con un corte
acumulado de eventos. Por defecto se busca `parte2/eventos.json` en Gold.

| Variable opcional | Uso |
| --- | --- |
| `PART2_EVENTS_BLOB` | Cambia la ruta del corte dentro de Gold. |
| `PART2_EVENTS_URL` | Si se configura, lee un endpoint HTTPS en lugar del blob. |

No hace falta agregar estas variables para habilitar las rutas. Solo se configuran
si el productor publica el corte en otra ubicación. La respuesta HTTPS se limita
a 10 MB y tiene un timeout de 5 segundos.

```json
{
  "actualizado_en": "2026-11-16T18:00:00Z",
  "cobertura": ["culture", "emergencies"],
  "casos_por_referencia": {"id-del-evento-publico": 3},
  "eventos": []
}
```

`cobertura` debe declarar únicamente conjuntos completos para el período. Cada
evento lleva `metadata.eventId`, `metadata.eventType` y `data`. Los cálculos
usan identificadores únicos y excluyen backfill en los vínculos de emergencias.
Un corte completo sin eventos puede representar ceros reales; omitir cobertura
mantiene esos indicadores pendientes. No publicar el ejemplo vacío como datos
productivos salvo que represente el corte real.

## HTTP y actualización

- `200`: JSON validado, con `Cache-Control: private, no-store`.
- `401/403`: se mantiene el rechazo de solicitudes sin sesión o sin permisos,
  antes de leer Storage.
- `422`: nombre de área no admitido.
- `503`: fuente inaccesible, corte inválido o configuración incompleta; mensaje
  genérico sin URLs privadas ni credenciales.

La web consulta cada 15 segundos cuando la ruta existe. Si recibe `404`, detiene
el polling de esa área hasta un reintento manual o una nueva carga de la pantalla;
un reintento exitoso vuelve a habilitar el refresco. Los fallos transitorios
conservan el último corte y mantienen los reintentos.

El HTML embed incluye los indicadores disponibles en el bloque `parte2` del
JSON inyectado y no consulta estas rutas desde el iframe. Para recibir un corte
nuevo hay que solicitar nuevamente el HTML y contemplar la caché interna del backend.
