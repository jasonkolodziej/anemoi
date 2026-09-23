"""Anemoi-branded ReDoc (anemoi.api.docs, #159)."""

from __future__ import annotations

import warnings

import pytest

pytest.importorskip("fastapi")

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from fastapi.testclient import TestClient  # noqa: E402

pytestmark = [
    pytest.mark.api,
    pytest.mark.filterwarnings("ignore::DeprecationWarning"),
]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from anemoi.api import demo_state

    demo_state._STATE = None
    from anemoi.api.main import app

    return TestClient(app)


def test_redoc_route_replaces_the_unstyled_default(client):
    r = client.get("/redoc")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    # The default get_redoc_html's declarative element -- confirms this is
    # genuinely the custom route, not FastAPI's stock one still mounted.
    assert "<redoc spec-url" not in r.text
    assert "Redoc.init(" in r.text
    assert '"/openapi.json"' in r.text


def test_redoc_embeds_the_real_theme_json(client):
    from anemoi.api.docs import REDOC_THEME

    r = client.get("/redoc")
    # Every branded colour must actually be present in the served HTML,
    # not just in the Python dict that was supposed to produce it.
    assert REDOC_THEME["colors"]["primary"]["main"] in r.text
    assert REDOC_THEME["sidebar"]["backgroundColor"] in r.text
    assert REDOC_THEME["colors"]["http"]["get"] in r.text
    assert REDOC_THEME["colors"]["http"]["delete"] in r.text


def test_redoc_theme_css_is_served(client):
    r = client.get("/static/redoc-theme.css")
    assert r.status_code == 200
    assert "text/css" in r.headers["content-type"]
    assert "#0a0e17" in r.text.lower()


def test_redoc_links_the_static_theme_css(client):
    r = client.get("/redoc")
    assert '/static/redoc-theme.css' in r.text


def test_theme_never_uses_a_god_color():
    """Branding.md's own rule: the six god colours are data colours and
    must never appear anywhere else (track lines, status badges, run tags
    -- and now, API docs chrome). Mirrors test_branding.py's own
    `test_structural_colors_are_never_model_colors` for this new consumer."""
    from anemoi import branding
    from anemoi.api.docs import REDOC_THEME

    god_colors = {g.color.upper() for g in branding.GODS}

    def _walk(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                yield from _walk(v)
        elif isinstance(obj, str):
            yield obj.upper()

    all_theme_strings = set(_walk(REDOC_THEME))
    assert not (god_colors & all_theme_strings), (
        f"a god colour leaked into REDOC_THEME: {god_colors & all_theme_strings}"
    )


def test_theme_http_method_colors_are_distinct():
    """A real usability property, not decoration: GET/POST/PUT/PATCH/DELETE
    badges must be visually distinguishable from each other."""
    from anemoi.api.docs import REDOC_THEME

    http_colors = list(REDOC_THEME["colors"]["http"].values())
    assert len(http_colors) == len(set(http_colors))


def test_docs_route_is_unaffected():
    """redoc_url=None must not have touched /docs (Swagger UI) -- these are
    independent routes in FastAPI, and this issue only asked for ReDoc."""
    from anemoi.api.main import app

    assert app.docs_url == "/docs"
