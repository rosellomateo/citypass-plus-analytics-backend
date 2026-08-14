from fastapi import FastAPI

app = FastAPI(
    title="CityPass+ Analytics API",
    description="Urban Analytics and AI/ML module for CityPass+.",
    version="0.1.0",
)


@app.get("/", status_code=200)
async def root() -> dict[str, str]:
    return {"message": "OK"}
