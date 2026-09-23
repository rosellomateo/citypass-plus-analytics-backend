# Despliegue y CI/CD

## Flujos de GitHub Actions

El repositorio contiene tres workflows:

| Archivo | Disparador | Objetivo |
| --- | --- | --- |
| `.github/workflows/ci.yml` | Push o pull request a `main` y `develop` | Formato, lint, pruebas, validación de Compose, build de producción y smoke test de `/health`. |
| `.github/workflows/develop_rg-citypass-backend-test.yml` | Push a `develop` o ejecución manual | Despliegue del código en Azure Web App `rg-citypass-backend-test`. |
| `.github/workflows/deploy-production.yml` | Push a `main` o ejecución manual | Valida el proyecto, despliega la Web App productiva y comprueba `/health` y la conexión Gold. |

## Entorno de test

El despliegue existente de `develop` usa OpenID Connect y referencia estos
secretos:

- `AZUREAPPSERVICE_CLIENTID_B59C496BB1704620AFEB082C578133A9`
- `AZUREAPPSERVICE_TENANTID_6482AAF165B249D0AF8F3E2FED23F896`
- `AZUREAPPSERVICE_SUBSCRIPTIONID_B5BDDA8BC43B46808B5ABBC85F0E702C`

Los valores deben existir en GitHub Actions y la identidad federada debe tener
permisos sobre la Web App. Los nombres no son credenciales, pero sus valores sí
son secretos.

## Entorno de producción

El workflow de `main` usa el GitHub Environment `production`. Debe contener:

| Tipo | Nombre | Uso |
| --- | --- | --- |
| Variable | `AZURE_WEBAPP_NAME` | Nombre de la Web App productiva. |
| Variable | `BACKEND_PUBLIC_URL` | URL HTTPS pública, usada para mostrar el deployment y probar `/health`. |
| Secreto | `AZURE_CLIENT_ID` | Client ID de la identidad usada por OIDC. |
| Secreto | `AZURE_TENANT_ID` | Tenant ID de Azure. |
| Secreto | `AZURE_SUBSCRIPTION_ID` | Subscription ID que contiene la Web App. |

La identidad federada debe aceptar el subject correspondiente al environment
`production` y tener permisos de despliegue sobre la Web App productiva. El
workflow valida que todos estos valores existan antes de iniciar sesión en Azure.

## Configuración requerida en Azure Web App

Configurar como Application Settings:

- `AZURE_STORAGE_ACCOUNT_URL`
- `AZURE_STORAGE_CONTAINER`
- `AZURE_STORAGE_SAS_TOKEN`
- `CORS_ALLOWED_ORIGINS`, con la URL pública exacta del frontend

La configuración pertenece al entorno de Azure, no al artefacto desplegado. Los
workflows no crean ni actualizan estas variables.

La aplicación debe iniciarse con Python 3.12 y un comando equivalente a:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Configurar `/health` como ruta de comprobación de estado de la plataforma. Este
endpoint no depende de Azure Storage.

## Secuencia de despliegue recomendada

1. Verificar localmente la suite, el health check y al menos una consulta Gold.
2. Configurar las Application Settings y los secretos OIDC.
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
- [ ] `CORS_ALLOWED_ORIGINS` contiene el dominio HTTPS del frontend.
- [ ] La Web App inicia Uvicorn correctamente.
- [ ] `/health` responde `200`.
- [ ] Las rutas de analítica leen la capa Gold.
- [ ] Los secretos no aparecen en commits ni logs.
- [ ] Se reconoce que autenticación/autorización todavía está pendiente.

## Rollback

Ante un fallo, usar el historial de despliegues de Azure o volver a desplegar el
último commit estable. Rotar inmediatamente el SAS si se expuso en un log,
captura, commit o mensaje.
