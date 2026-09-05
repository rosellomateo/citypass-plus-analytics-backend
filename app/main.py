from fastapi import FastAPI
from app.routers.rout_espacios_cultura import router as espacio_cultura_router
from app.routers.rout_eventos import router as eventos_router
from app.routers.rout_movilidad_urbana import router as movilidad_urbana_router
from app.routers.rout_reclamos import router as reclamos_router
from app.routers.rout_residuos import router as residuos_router
from app.routers.rout_seguridad_emergencias import router as seguridad_emergencias_router


app = FastAPI(
    title="CityPass+ Analytics API",
    description="Urban Analytics and AI/ML module for CityPass+.",
    version="0.1.0",
)

app.include_router(espacio_cultura_router)
app.include_router(eventos_router)
app.include_router(movilidad_urbana_router)
app.include_router(reclamos_router)
app.include_router(residuos_router)
app.include_router(seguridad_emergencias_router)


@app.get("/", status_code=200)
async def root() -> dict[str, str]:
    return {"message": "OK"}
