# Despliegue y CI/CD

## Flujos de GitHub Actions

El repositorio contiene tres workflows:

| Archivo | Disparador | Objetivo |
| --- | --- | --- |
| `.github/workflows/ci.yml` | Push o pull request a `main` y `develop` | Formato, lint, pruebas, validación de Compose, build de producción y smoke test de `/health`. |
| `.github/workflows/develop_rg-citypass-backend-test.yml` | Push a `develop` o ejecución manual | Publica la imagen en GHCR, despliega el contenedor de test y valida la conexión Gold. |
| `.github/workflows/deploy-production.yml` | Push a `main` o ejecución manual | Publica la imagen en GHCR, despliega el contenedor productivo y valida la conexión Gold. |

## Entorno de test

El despliegue de `develop` usa estos valores fijos:

| Dato | Valor |
| --- | --- |
| Web App | `rg-citypass-backend-test` |
| Resource Group | `rg-citypass-backend-test` |
| URL pública | `https://rg-citypass-backend-test-g0hdacdxccbdb6g5.brazilsouth-01.azurewebsites.net` |
| Imagen | `ghcr.io/rosellomateo/citypass-plus-analytics-backend:<commit-sha>` |

El repositorio debe contener estos secretos de GitHub Actions:

- `AZUREAPPSERVICE_CLIENTID_B59C496BB1704620AFEB082C578133A9`
- `AZUREAPPSERVICE_TENANTID_6482AAF165B249D0AF8F3E2FED23F896`
- `AZUREAPPSERVICE_SUBSCRIPTIONID_B5BDDA8BC43B46808B5ABBC85F0E702C`
- `GHCR_PULL_TOKEN`: PAT classic de GitHub con permiso `read:packages`.

Los valores deben existir en GitHub Actions y la identidad federada debe tener
permisos sobre la Web App. Los nombres no son credenciales, pero sus valores sí
son secretos.

## Entorno de producción

El workflow de `main` usa el GitHub Environment `production`. Debe contener:

| Tipo | Nombre | Uso |
| --- | --- | --- |
| Variable | `AZURE_WEBAPP_NAME` | Nombre de la Web App productiva. |
| Variable | `AZURE_RESOURCE_GROUP` | Resource Group que contiene la Web App. |
| Variable | `BACKEND_PUBLIC_URL` | URL HTTPS pública, usada para mostrar el deployment y probar `/health`. |
| Secreto | `AZURE_CLIENT_ID` | Client ID de la identidad usada por OIDC. |
| Secreto | `AZURE_TENANT_ID` | Tenant ID de Azure. |
| Secreto | `AZURE_SUBSCRIPTION_ID` | Subscription ID que contiene la Web App. |
| Secreto | `GHCR_PULL_TOKEN` | PAT classic con `read:packages` para que App Service descargue la imagen privada. |

La identidad federada debe aceptar el subject correspondiente al environment
`production` y tener permisos de despliegue sobre la Web App productiva. El
workflow valida que todos estos valores existan antes de iniciar sesión en Azure.

## Configuración requerida en Azure Web App

Configurar como Application Settings:

- `AZURE_STORAGE_ACCOUNT_URL`
- `AZURE_STORAGE_CONTAINER`
- `AZURE_STORAGE_SAS_TOKEN`
- `AZURE_ANALISIS_ACCOUNT_URL`
- `AZURE_ANALISIS_CONTAINER`
- `AZURE_ANALISIS_SAS_TOKEN`
- `CORS_ALLOWED_ORIGINS`, con la URL pública exacta del frontend

La configuración pertenece al entorno de Azure, no al artefacto desplegado. Los
workflows no crean ni actualizan estas variables. Sí configuran automáticamente
`WEBSITES_PORT=8000`, las credenciales de lectura de GHCR y la imagen identificada
por el SHA del commit.

No se debe configurar un startup command en la Web App. La imagen usa el comando
de producción definido en el Dockerfile:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Configurar `/health` como ruta de comprobación de estado de la plataforma. Este
endpoint no depende de Azure Storage.

La credencial federada de producción debe usar el environment de GitHub, no la
rama directamente:

```text
repo:rosellomateo/citypass-plus-analytics-backend:environment:production
```

## Flujo del contenedor

1. El job `quality` ejecuta formato, lint y pruebas.
2. El job `build` construye el target Docker `production`.
3. GitHub Actions publica la imagen privada en GHCR usando `GITHUB_TOKEN`.
4. El job `deploy` inicia sesión en Azure mediante OIDC.
5. El workflow configura GHCR y el puerto del contenedor en la Web App.
6. App Service descarga la imagen etiquetada con el SHA del commit.
7. El pipeline comprueba `/health` y `/analytics/residuos`.

`GITHUB_TOKEN` se usa solamente para publicar desde el workflow. La Web App usa
`GHCR_PULL_TOKEN` porque necesita descargar la imagen después de que el job haya
terminado.

## Secuencia de despliegue recomendada

1. Verificar localmente la suite, el health check y al menos una consulta Gold.
2. Configurar las Application Settings, los secretos OIDC y `GHCR_PULL_TOKEN`.
3. Integrar la rama aprobada en `main` para ejecutar el workflow productivo.
4. Esperar que CI y despliegue finalicen correctamente.
5. Probar `https://<backend>/health`.
6. Probar un endpoint `/analytics/*` desde Postman.
7. Configurar el frontend con la URL pública confirmada del backend.

La ejecución manual permite volver a desplegar el commit actual de `main` desde
la pestaña Actions. El grupo de concurrencia evita superponer dos despliegues
productivos.

## Lista de verificación

- [ ] El SAS está vigente y solo posee los permisos necesarios.
- [ ] `GHCR_PULL_TOKEN` posee únicamente `read:packages` y no está vencido.
- [ ] `CORS_ALLOWED_ORIGINS` contiene el dominio HTTPS del frontend.
- [ ] La Web App está configurada como Container sobre Linux.
- [ ] La imagen del commit existe en GitHub Packages.
- [ ] La Web App inicia Uvicorn en el puerto 8000.
- [ ] `/health` responde `200`.
- [ ] Las rutas de analítica leen la capa Gold.
- [ ] Los secretos no aparecen en commits ni logs.
- [ ] Se reconoce que autenticación/autorización todavía está pendiente.

## Rollback

Ante un fallo, volver a desplegar la imagen de un commit estable. Rotar
inmediatamente el SAS o el PAT si se expusieron en un log, captura, commit o
mensaje.
