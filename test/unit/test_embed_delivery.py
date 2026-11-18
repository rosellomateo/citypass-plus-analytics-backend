import hashlib
import json
from contextlib import nullcontext
from html.parser import HTMLParser
from unittest.mock import Mock

import pytest
from azure.core.exceptions import ResourceNotFoundError
from fastapi.testclient import TestClient

from app.core import embed as embed_dependencies
from app.core.config import ConfigurationError, EmbedSettings
from app.main import create_app
from app.repositories import embed_template_repository
from app.repositories.embed_template_repository import (
    MODULOS_EMBED,
    MODULOS_EMBED_BASE,
    EmbedTemplateRepository,
    InvalidEmbedRelease,
)
from app.routers import rout_embed
from app.services import embed_service
from app.services.embed_service import EmbedService, EmbedUnavailableError
from test.unit.test_routers import FakeJsonRepository, FakeParquetRepository

RELEASE = "a" * 40
SETTINGS = EmbedSettings("https://citypassstorage.blob.core.windows.net", RELEASE)
TEMPLATE = (
    '<!doctype html><html lang="es" data-modulo="__CITYPASS_MODULO__"><body>'
    '<div id="root"></div><script id="citypass-datos" type="application/json">'
    '__CITYPASS_DATOS__</script><script type="module">window.rendered=true;</script></body></html>'
)


def make_release(template=TEMPLATE, **changes):
    html = template.encode()
    manifest = {
        "schemaVersion": 1,
        "commit": RELEASE,
        "modules": sorted(MODULOS_EMBED),
        "template": "embed.html",
        "sha256": hashlib.sha256(html).hexdigest(),
        "bytes": len(html),
    }
    manifest.update(changes)
    manifest_bytes = json.dumps(manifest).encode()
    return {
        "embed.html": html,
        "manifest.json": manifest_bytes,
        "SHA256SUMS": (
            f"{hashlib.sha256(html).hexdigest()}  embed.html\n"
            f"{hashlib.sha256(manifest_bytes).hexdigest()}  manifest.json\n"
        ).encode(),
    }


def make_repository(monkeypatch, files=None, settings=SETTINGS):
    files = make_release() if files is None else files
    container = Mock()

    def get_blob(name):
        assert name.startswith(f"releases/{RELEASE}/")
        blob = Mock()

        def download(offset, length):
            try:
                data = files[name.rsplit("/", 1)[1]]
            except KeyError:
                raise ResourceNotFoundError("private detail") from None
            return Mock(readall=lambda: data[offset : offset + length])

        blob.download_blob.side_effect = download
        return blob

    container.get_blob_client.side_effect = get_blob
    repository = EmbedTemplateRepository(settings)
    monkeypatch.setattr(repository, "_open_container", lambda: nullcontext(container))
    return repository, container


class PayloadParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.in_payload = False
        self.payload = ""
        self.scripts = 0
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.scripts += 1
            self.in_payload = dict(attrs).get("id") == "citypass-datos"

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_payload = False

    def handle_data(self, data):
        if self.in_payload:
            self.payload += data


@pytest.fixture
def client(monkeypatch):
    application = create_app()
    templates = Mock(load=Mock(return_value=TEMPLATE))
    payloads = Mock(side_effect=lambda module: {"datos": [{"module": module}], "informe": {}})
    service = EmbedService(SETTINGS, templates, payloads)
    monkeypatch.setattr(rout_embed, "obtener_servicio_embed", lambda: service)

    def authorized(modulo: str):
        return {"sub": "U42", "jti": "test", "namespace": f"com.citypass.{modulo}"}

    application.dependency_overrides[rout_embed.autorizar_embed] = authorized
    with TestClient(application) as http:
        yield http, templates, payloads, service


@pytest.mark.parametrize("module", sorted(MODULOS_EMBED))
def test_returns_html_with_exact_payload_and_security_headers(client, module):
    http, _, payloads, _ = client
    response = http.get(f"/embed/{module}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert response.headers["cache-control"] == "private, no-store"
    assert (
        response.headers["content-security-policy"]
        == rout_embed.CABECERAS["Content-Security-Policy"]
    )
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert f'data-modulo="{module}"' in response.text
    assert "__CITYPASS_" not in response.text
    assert json.loads(PayloadParser(response.text).payload) == {
        "datos": [{"module": module}],
        "informe": {},
    }
    payloads.assert_called_once_with(module)


def test_json_cannot_close_the_script_block(client):
    http, _, payloads, _ = client
    malicious = '</script><script>alert("xss")</script><img src=x onerror=alert(1)>'
    payloads.side_effect = None
    payloads.return_value = {"datos": [{"texto": malicious}], "informe": {}}
    response = http.get("/embed/reclamos")
    parser = PayloadParser(response.text)
    assert parser.scripts == 2
    assert malicious not in response.text
    assert json.loads(parser.payload)["datos"][0]["texto"] == malicious


def test_caches_html_by_module_and_template_by_release(client):
    http, templates, payloads, _ = client
    first = http.get("/embed/reclamos")
    assert http.get("/embed/reclamos").text == first.text
    assert http.get("/embed/residuos").status_code == 200
    assert [call.args[0] for call in payloads.call_args_list] == ["reclamos", "residuos"]
    templates.load.assert_called_once_with()


def test_expired_cache_reloads_data_but_not_the_immutable_template():
    now = [0.0]
    templates = Mock(load=Mock(return_value=TEMPLATE))
    payloads = Mock(return_value={"datos": [], "informe": {}})
    service = EmbedService(SETTINGS, templates, payloads, clock=lambda: now[0])
    service.render("reclamos")
    now[0] = 599
    service.render("reclamos")
    assert payloads.call_count == 1
    now[0] = 600
    service.render("reclamos")
    assert payloads.call_count == 2
    templates.load.assert_called_once_with()


def test_authentication_runs_again_on_cached_response(client):
    http, _, payloads, _ = client
    assert http.get("/embed/reclamos").status_code == 200
    del http.app.dependency_overrides[rout_embed.autorizar_embed]
    assert http.get("/embed/reclamos").status_code == 401
    assert payloads.call_count == 1


@pytest.mark.parametrize("failure", ["template", "data"])
def test_storage_or_data_failure_is_generic_503_and_is_not_cached(client, failure, caplog):
    http, templates, payloads, _ = client
    target = templates.load if failure == "template" else payloads
    target.side_effect = ResourceNotFoundError("sig=secret-and-private-data")
    response = http.get("/embed/reclamos")
    assert response.status_code == 503
    assert response.json() == {"detail": "Analítica no disponible"}
    assert response.headers["cache-control"] == "private, no-store"
    assert "secret" not in response.text + caplog.text
    if failure == "template":
        target.side_effect = None
        target.return_value = TEMPLATE
    else:
        target.side_effect = lambda module: {"datos": [], "informe": {}}
    assert http.get("/embed/reclamos").status_code == 200


def test_identidad_returns_html_and_loads_data(client, caplog):
    http, templates, payloads, _ = client
    with caplog.at_level("INFO", logger="app.routers.rout_embed"):
        response = http.get("/embed/identidad")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert json.loads(PayloadParser(response.text).payload)["datos"] == [{"module": "identidad"}]
    templates.load.assert_called_once_with()
    payloads.assert_called_once_with("identidad")
    assert "embed modulo=identidad usuario=U42" in caplog.text


def test_lazy_configuration_does_not_break_health_and_fails_closed(monkeypatch):
    monkeypatch.delenv("EMBED_STORAGE_ACCOUNT_URL", raising=False)
    embed_dependencies.obtener_servicio_embed.cache_clear()
    application = create_app()
    application.dependency_overrides[rout_embed.autorizar_embed] = lambda: {"sub": "test"}
    with TestClient(application) as http:
        assert http.get("/health").status_code == 200
        response = http.get("/embed/reclamos")
        assert response.status_code == 503
        assert response.headers["cache-control"] == "private, no-store"
    embed_dependencies.obtener_servicio_embed.cache_clear()


def test_loads_and_verifies_a_complete_release(monkeypatch):
    repository, container = make_repository(monkeypatch)
    assert repository.load() == TEMPLATE
    assert all(repository.supports_module(module) for module in MODULOS_EMBED)
    assert [call.args[0] for call in container.get_blob_client.call_args_list] == [
        f"releases/{RELEASE}/SHA256SUMS",
        f"releases/{RELEASE}/manifest.json",
        f"releases/{RELEASE}/embed.html",
    ]


@pytest.mark.parametrize("missing", ["SHA256SUMS", "manifest.json", "embed.html"])
def test_rejects_incomplete_release(monkeypatch, missing):
    files = make_release()
    del files[missing]
    repository, _ = make_repository(monkeypatch, files)
    with pytest.raises(ResourceNotFoundError):
        repository.load()


@pytest.mark.parametrize("filename", ["embed.html", "manifest.json"])
def test_rejects_modified_remote_files(monkeypatch, filename):
    files = make_release()
    files[filename] += b"corrupted"
    repository, _ = make_repository(monkeypatch, files)
    with pytest.raises(InvalidEmbedRelease):
        repository.load()


@pytest.mark.parametrize(
    "changes",
    [
        {"commit": "b" * 40},
        {"schemaVersion": 2},
        {"schemaVersion": True},
        {"template": "../other.html"},
        {"modules": ["identidad"]},
        {"modules": [1]},
        {"modules": sorted(MODULOS_EMBED) + ["eda"]},
        {"modules": sorted(MODULOS_EMBED) + ["identidad"]},
        {"sha256": "0" * 64},
        {"bytes": 1},
    ],
)
def test_rejects_manifest_for_wrong_release_or_contents(monkeypatch, changes):
    repository, _ = make_repository(monkeypatch, make_release(**changes))
    with pytest.raises(InvalidEmbedRelease):
        repository.load()


@pytest.mark.parametrize("sums", [b"", b"invalid", b"0" * 64 + b"  ../embed.html\n"])
def test_rejects_invalid_checksum_file(monkeypatch, sums):
    files = make_release()
    files["SHA256SUMS"] = sums
    repository, _ = make_repository(monkeypatch, files)
    with pytest.raises(InvalidEmbedRelease):
        repository.load()


@pytest.mark.parametrize("template", ["<html>missing placeholders</html>", TEMPLATE + TEMPLATE])
def test_rejects_incompatible_template_even_with_matching_hashes(monkeypatch, template):
    repository, _ = make_repository(monkeypatch, make_release(template))
    with pytest.raises(InvalidEmbedRelease):
        repository.load()


def test_limits_template_download_size(monkeypatch):
    settings = EmbedSettings(SETTINGS.account_url, RELEASE, max_template_bytes=10)
    repository, _ = make_repository(monkeypatch, settings=settings)
    with pytest.raises(InvalidEmbedRelease, match="tamaño"):
        repository.load()


def test_closes_azure_client_and_credential_on_failure(monkeypatch):
    credential = Mock()
    credential.__enter__ = Mock(return_value=credential)
    credential.__exit__ = Mock(return_value=False)
    container = Mock()
    container.__enter__ = Mock(return_value=container)
    container.__exit__ = Mock(return_value=False)
    container.get_blob_client.return_value.download_blob.side_effect = ResourceNotFoundError()
    credential_factory = Mock(return_value=credential)
    container_factory = Mock(return_value=container)
    monkeypatch.setattr(embed_template_repository, "DefaultAzureCredential", credential_factory)
    monkeypatch.setattr(embed_template_repository, "ContainerClient", container_factory)
    repository = EmbedTemplateRepository(SETTINGS)
    with pytest.raises(ResourceNotFoundError):
        repository.load()
    credential.__exit__.assert_called_once()
    container.__exit__.assert_called_once()
    assert container_factory.call_args.kwargs["credential"] is credential
    assert container_factory.call_args.kwargs["container_name"] == "plantillas"


@pytest.mark.parametrize("module", sorted(MODULOS_EMBED))
def test_payload_matches_existing_analytics_services_and_closes_repositories(monkeypatch, module):
    gold = FakeParquetRepository()
    reports = FakeJsonRepository()
    closed = []

    def gold_context():
        try:
            yield gold
        finally:
            closed.append("gold")

    def reports_context():
        try:
            yield reports
        finally:
            closed.append("reports")

    monkeypatch.setattr(embed_service, "obtener_repositorio", gold_context)
    monkeypatch.setattr(embed_service, "obtener_repositorio_informes", reports_context)
    monkeypatch.setattr(embed_service, "cargar_parte2", lambda modulo: {"datos": [modulo]})
    expected = embed_service.SERVICIOS[module](gold, reports).model_dump(mode="json")
    if module != "identidad":
        # Parte 2 se agrega aparte; lo que ya se mandaba no cambia.
        expected["parte2"] = {"datos": [module]}
    assert embed_service.cargar_payload(module) == expected
    assert closed == ["reports", "gold"]


@pytest.mark.parametrize(
    ("module", "area"),
    [
        ("reclamos", "claims"),
        ("emergencias", "emergencies"),
        ("movilidad", "mobility"),
        ("espacios", "culture"),
        ("residuos", "waste"),
    ],
)
def test_embed_parte2_uses_the_same_indicators_as_the_portal(monkeypatch, module, area):
    from app.routers.rout_parte2 import Indicador, IndicadoresParteDos

    pedidos = []

    def leer(requested):
        pedidos.append(requested)
        return IndicadoresParteDos(datos=[Indicador(id="c5", valor=3)])

    monkeypatch.setattr(embed_service, "leer_indicadores", leer)
    assert embed_service.cargar_parte2(module)["datos"][0]["id"] == "c5"
    assert pedidos == [area]


def test_embed_without_parte2_still_delivers_the_dashboard(monkeypatch):
    from fastapi import HTTPException

    def falla(area):
        raise HTTPException(503, "No se pudieron consultar los indicadores")

    monkeypatch.setattr(embed_service, "leer_indicadores", falla)
    assert embed_service.cargar_parte2("residuos") is None
    assert embed_service.cargar_parte2("identidad") is None


def test_cannot_render_an_unsupported_module():
    service = EmbedService(SETTINGS, Mock())
    with pytest.raises(ValueError):
        service.render("eda")


@pytest.mark.parametrize("identity_first", [False, True])
def test_old_release_keeps_five_modules_working_and_does_not_render_identity(
    monkeypatch, identity_first
):
    repository, container = make_repository(
        monkeypatch, make_release(modules=sorted(MODULOS_EMBED_BASE))
    )
    payloads = Mock(return_value={"datos": [], "informe": {}})
    service = EmbedService(SETTINGS, repository, payloads)
    if identity_first:
        with pytest.raises(EmbedUnavailableError):
            service.render("identidad")
        payloads.assert_not_called()
    for module in sorted(MODULOS_EMBED_BASE):
        assert f'data-modulo="{module}"' in service.render(module)
    with pytest.raises(EmbedUnavailableError):
        service.render("identidad")
    assert payloads.call_count == 5
    assert container.get_blob_client.call_count == 3


@pytest.mark.parametrize("with_report", [True, False])
def test_identidad_html_includes_analytics_data_with_optional_report(monkeypatch, with_report):
    repository, _ = make_repository(monkeypatch)
    reports = FakeJsonRepository()
    if not with_report:
        error = ResourceNotFoundError("private storage details")
        error.error_code = "BlobNotFound"
        reports.read = Mock(side_effect=error)
    payload = embed_service.SERVICIOS["identidad"](FakeParquetRepository(), reports).model_dump(
        mode="json"
    )
    service = EmbedService(SETTINGS, repository, Mock(return_value=payload))
    application = create_app()
    application.dependency_overrides[rout_embed.autorizar_embed] = lambda: {
        "sub": "U42",
        "jti": "test",
    }
    monkeypatch.setattr(rout_embed, "obtener_servicio_embed", lambda: service)
    with TestClient(application) as http:
        response = http.get("/embed/identidad")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert response.headers["cache-control"] == "private, no-store"
    injected = json.loads(PayloadParser(response.text).payload)
    assert injected == payload
    assert injected["datos"][0]["cantidadEventos"] == 3_000_000_000
    assert (injected["informe"] is not None) == with_report


def test_identity_with_old_release_returns_503_without_loading_data(monkeypatch):
    repository, _ = make_repository(monkeypatch, make_release(modules=sorted(MODULOS_EMBED_BASE)))
    payloads = Mock()
    service = EmbedService(SETTINGS, repository, payloads)
    application = create_app()
    application.dependency_overrides[rout_embed.autorizar_embed] = lambda: {
        "sub": "U42",
        "jti": "test",
    }
    monkeypatch.setattr(rout_embed, "obtener_servicio_embed", lambda: service)
    with TestClient(application) as http:
        response = http.get("/embed/identidad")
    assert response.status_code == 503
    assert response.json() == {"detail": "Analítica no disponible"}
    assert response.headers["cache-control"] == "private, no-store"
    payloads.assert_not_called()


def test_invalid_payload_does_not_populate_cache():
    templates = Mock(load=Mock(return_value=TEMPLATE))
    payloads = Mock(return_value={"value": float("nan")})
    service = EmbedService(SETTINGS, templates, payloads)
    with pytest.raises(EmbedUnavailableError):
        service.render("reclamos")
    payloads.return_value = {"datos": [], "informe": {}}
    assert "NaN" not in service.render("reclamos")


def test_embed_settings_defaults_and_identity(monkeypatch):
    monkeypatch.setenv("EMBED_STORAGE_ACCOUNT_URL", SETTINGS.account_url + "/")
    monkeypatch.setenv("EMBED_RELEASE_SHA", RELEASE)
    monkeypatch.setenv("EMBED_MANAGED_IDENTITY_CLIENT_ID", "managed-client")
    settings = EmbedSettings.from_environment()
    assert settings.account_url == SETTINGS.account_url
    assert settings.container_name == "plantillas"
    assert settings.release_prefix == f"releases/{RELEASE}"
    assert settings.cache_ttl_seconds == 600
    assert settings.managed_identity_client_id == "managed-client"


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("EMBED_STORAGE_ACCOUNT_URL", "http://storage.blob.core.windows.net"),
        ("EMBED_STORAGE_ACCOUNT_URL", "https://storage.blob.core.windows.net?sig=secret"),
        ("EMBED_STORAGE_ACCOUNT_URL", "https://storage.blob.core.windows.net/plantillas"),
        ("EMBED_RELEASE_SHA", "latest"),
        ("EMBED_RELEASE_SHA", "../embed.html"),
        ("EMBED_STORAGE_CONTAINER", "$web"),
        ("EMBED_STORAGE_CONTAINER", "BadName"),
        ("EMBED_CACHE_TTL_SEGUNDOS", "invalid"),
        ("EMBED_CACHE_TTL_SEGUNDOS", "-1"),
    ],
)
def test_invalid_embed_configuration(monkeypatch, name, value):
    monkeypatch.setenv("EMBED_STORAGE_ACCOUNT_URL", SETTINGS.account_url)
    monkeypatch.setenv("EMBED_RELEASE_SHA", RELEASE)
    monkeypatch.setenv(name, value)
    with pytest.raises(ConfigurationError):
        EmbedSettings.from_environment()
