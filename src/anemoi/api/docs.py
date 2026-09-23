"""Anemoi-branded ReDoc (#159).

Scope PLAN.md "UI / UX" row. FastAPI's built-in ``/redoc`` route
(``fastapi.openapi.docs.get_redoc_html``) renders the open-source ``redoc``
npm package (pinned to its ``@2`` major line -- the same CDN default FastAPI
itself uses) with no styling hook at all: no ``theme`` argument, nothing.
Its own docstring says as much -- "You would only call this function
yourself if you needed to override some parts."

**A real correction to how this issue was originally scoped.** The issue's
two reference links are both real, but only one of them applies here:
Redocly's `customize-styles
<https://redocly.com/docs/realm/branding/customize-styles>`_ guide (a plain
``@theme/styles.css`` of CSS custom properties like ``--color-primary``) is
for **Redocly Realm**, a separate paid product -- verified by fetching that
page directly, not assumed. It has no effect on the open-source ``redoc``
bundle FastAPI actually embeds; a ``:root { --color-primary: ... }`` file
declared per that guide would load without error and silently do nothing.
The real mechanism for the open-source bundle (confirmed against
`Redocly/redoc`'s own ``src/theme.ts``) is a nested JS object --
``ThemeInterface`` -- passed to ``Redoc.init(specUrl, {theme}, element)``,
not a CSS file. :data:`REDOC_THEME` below is that object.

A real, small CSS file (``static/redoc-theme.css``) is still declared and
served, honoring the issue's own deliverable -- it covers what the JS theme
object does not: the ``<body>`` background before ``redoc.standalone.js``
finishes loading and mounts (otherwise a white flash against this app's
dark-only palette), and the scrollbar.

Every colour below is pulled from :mod:`anemoi.branding` -- the wiki's own
Branding.md rule ("``anemoi.branding`` is the only place the mapping lives.
Never hard-code it a second time") applies here exactly as it does to any
other consumer. The neutral scale (background/surface/border/text) has no
``branding.py`` equivalent yet -- it lives only in the console's
``app.css``/``branding.ts`` today (Branding.md's "Console theme" section) --
so those few hex values are named constants here, each commented with the
console token they mirror, not re-derived or guessed.

**Colour-rule compliance, checked against Branding.md's own rule** ("the six
god colours are data colours... never assign to a model, and never let it
appear anywhere else"): no ``WindGod.color`` appears anywhere in
:data:`REDOC_THEME`. HTTP method badges and status semantics are drawn from
``branding.STATUS_COLORS``/``FUNCTIONAL_COLORS`` instead -- the same
non-god, semantic tier the console's own Model Pantheon status badges use.
``tests/test_api_docs.py::test_theme_never_uses_a_god_color`` asserts this
structurally, the same way ``test_structural_colors_are_never_model_colors``
already does for the console/branding module itself.
"""

from __future__ import annotations

import json

from fastapi.responses import HTMLResponse

from .. import branding

#: Storm Dark neutral scale -- mirrors console/src/app.css's --color-bg/
#: --color-surface/--color-border/--color-text exactly (Branding.md's
#: "Console theme" table). No branding.py equivalent exists yet (that
#: module only carries the god/status/functional *data* colours, not the
#: neutral UI-chrome scale), so these few are named here instead of
#: silently duplicated as bare hex literals inline below.
_BG = "#0A0E17"  # console --color-bg
_SURFACE = "#111827"  # console --color-surface
_BORDER = "#1E293B"  # console --color-border
_TEXT = branding.FUNCTIONAL_COLORS["Eye"]  # #F8FAFC, == console --color-text
_TEXT_MUTED = branding.FUNCTIONAL_COLORS["Cirrus"]  # #94A3B8
_ACTION = "#60A5FA"  # console --color-action, the one interactive hue

#: The real, nested Redoc v2 `ThemeInterface` shape (Redocly/redoc's own
#: src/theme.ts) -- passed as JSON into `Redoc.init`'s second argument by
#: `get_custom_redoc_html` below. Every branded value traces to
#: `anemoi.branding` or, for the neutral scale, the constants just above;
#: nothing here is a value invented for this file alone.
REDOC_THEME: dict = {
    "colors": {
        "primary": {"main": _ACTION},
        "text": {"primary": _TEXT, "secondary": _TEXT_MUTED},
        "border": {"dark": _BORDER, "light": _BORDER},
        "http": {
            # Non-god, semantic colours only -- see this module's own
            # docstring on colour-rule compliance.
            "get": branding.STATUS_COLORS["online"],  # Clear, #22D3EE
            "post": _ACTION,
            "put": branding.STATUS_COLORS["training"],  # Euronotus, #FB923C
            "patch": branding.STATUS_COLORS["degraded"],  # Lips, #A3E635
            "delete": branding.FUNCTIONAL_COLORS["Landfall"],  # #F43F5E
        },
    },
    "sidebar": {
        "backgroundColor": _SURFACE,
        "textColor": _TEXT_MUTED,
        "activeTextColor": _ACTION,
    },
    "rightPanel": {
        "backgroundColor": _BG,
        "textColor": _TEXT,
    },
    "typography": {
        # Matches console --font-sans/--font-display/--font-mono exactly
        # (Branding.md's typography table) -- Inter and Geist Mono are
        # loaded from Google Fonts by get_custom_redoc_html below (both
        # real web fonts on that CDN, the same way the console's own
        # app.html loads Geist Mono); Geist Variable (body) has no Google
        # Fonts CDN entry (Branding.md notes it's fontsource-only), so
        # body copy here falls through to the ui-sans-serif/system-ui tail
        # of the stack -- an honest, working fallback, not a broken font
        # reference.
        "fontFamily": "'Geist Variable', ui-sans-serif, system-ui, sans-serif",
        "headings": {"fontFamily": "'Inter Variable', ui-sans-serif, system-ui, sans-serif"},
        "code": {"fontFamily": "'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace"},
        "links": {"color": _ACTION},
    },
}

#: Pinned to the same major line FastAPI's own default `redoc_js_url`
#: already uses -- REDOC_THEME's shape was verified against redoc's theme
#: source for this line; a newer major could rename/restructure it.
REDOC_JS_URL = "https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js"

_GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Inter:wght@400;500;600;700&family=Geist+Mono:wght@400;500&display=swap"
)


def get_custom_redoc_html(*, openapi_url: str, title: str) -> HTMLResponse:
    """The real replacement for `fastapi.openapi.docs.get_redoc_html` --
    that function has no theming hook at all (see this module's own
    docstring), so reaching Redoc's actual theme API means calling
    `Redoc.init()` from a script instead of using its declarative
    ``<redoc spec-url="...">`` custom element, which cannot carry a
    nested JSON theme through an HTML attribute.
    """
    theme_json = json.dumps(REDOC_THEME)
    html = f"""\
<!DOCTYPE html>
<html>
<head>
<title>{title}</title>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link href="{_GOOGLE_FONTS_URL}" rel="stylesheet">
<link rel="stylesheet" href="/static/redoc-theme.css">
</head>
<body>
<noscript>
    ReDoc requires Javascript to function. Please enable it to browse the documentation.
</noscript>
<div id="redoc-container"></div>
<script src="{REDOC_JS_URL}"></script>
<script>
  Redoc.init(
    "{openapi_url}",
    {{theme: {theme_json}}},
    document.getElementById("redoc-container")
  );
</script>
</body>
</html>
"""
    return HTMLResponse(html)
