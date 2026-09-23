from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import CorsSettings
from app.routers.rout_espacios_cultura import router as espacio_cultura_router
from app.routers.rout_eventos import router as eventos_router
from app.routers.rout_movilidad_urbana import router as movilidad_urbana_router
from app.routers.rout_reclamos import router as reclamos_router
from app.routers.rout_residuos import router as residuos_router
from app.routers.rout_seguridad_emergencias import router as seguridad_emergencias_router


def create_app(cors_settings: CorsSettings | None = None) -> FastAPI:
    settings = cors_settings or CorsSettings.from_environment()
    application = FastAPI(
        title="CityPass+ Analytics API",
        description="Urban Analytics and AI/ML module for CityPass+.",
        version="0.1.0",
    )

    if settings.allowed_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.allowed_origins),
            allow_credentials=False,
            allow_methods=["GET", "OPTIONS"],
            allow_headers=["Accept", "Content-Type"],
        )

    application.include_router(espacio_cultura_router)
    application.include_router(eventos_router)
    application.include_router(movilidad_urbana_router)
    application.include_router(reclamos_router)
    application.include_router(residuos_router)
    application.include_router(seguridad_emergencias_router)

    @application.get("/", status_code=200)
    async def root() -> dict[str, str]:
        return {"message": "OK"}

    @application.get("/health", status_code=200, tags=["Health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
