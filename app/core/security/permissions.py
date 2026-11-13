"""Política de acceso a los paneles de la web de Analytics."""

GRUPO_ADMIN = "admin"


def es_admin(grupos: list[str]) -> bool:
    return GRUPO_ADMIN in grupos
