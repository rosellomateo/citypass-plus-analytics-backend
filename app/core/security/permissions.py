"""Política de acceso a los tableros del portal de Analítica."""

import os

MODULE_BY_AREA = {
    "overview": "analitica",
    "claims": "reclamos",
    "emergencies": "emergencias",
    "mobility": "movilidad",
    "culture": "espacios",
    "waste": "residuos",
    "login": "identidad",
    "dap": "dap",
    "eda": "eda",
}
ROLES = frozenset({"admin", "delegados", "operadores"})


def module_audiences(analytics_audience: str) -> dict[str, set[str]]:
    audiences = {module: {f"citypass-{module}-api"} for module in MODULE_BY_AREA.values()}
    audiences["analitica"] = {analytics_audience, "citypass-admin-api"}
    audiences["identidad"] = {os.getenv("JWT_LOGIN_AUDIENCE", "citypass-admin-api")}
    audiences["dap"] = {os.getenv("JWT_DAP_AUDIENCE", "citypass-dap-api")}
    return audiences


def canonical_module(value: str) -> str:
    aliases = {
        "login": "identidad",
        os.getenv("JWT_LOGIN_MODULE", "identidad"): "identidad",
        os.getenv("JWT_DAP_MODULE", "dap"): "dap",
    }
    return aliases.get(value, value)


def allowed_dashboards(module: str, groups: list[str]) -> list[str]:
    if module == "analitica" and {"admin", "analitica-urbana"}.intersection(groups):
        return list(MODULE_BY_AREA)
    if module == "analitica" or not ROLES.intersection(groups):
        return []
    return [area for area, owner in MODULE_BY_AREA.items() if owner == module]
