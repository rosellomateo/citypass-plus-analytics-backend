from pydantic import BaseModel


class UsuarioAutenticado(BaseModel):
    sub: str
    username: str | None = None
    groups: list[str]
    module: str
    jti: str | None = None
    expires_at: int | None = None
