"""Serving the built web application, when there is one.

**THE APPLICATION AND ITS API WERE NEVER ON THE SAME ORIGIN.** `vite` serves the
app on 1234, the container publishes the API on 2020, the trio runs it on 2718,
and `appsettings.json` — a build-time constant — said 8000. So a built bundle
could talk to exactly one machine's guess, and a person told "the web front end
is up" got a redirect to `/docs`: correct, and not what anybody meant.

Mounting `web/dist` here gives the ordinary single-origin arrangement, where the
page and its API answer on one port and nothing has to be configured. **It does
not replace `vite dev`**, which stays the way to develop: this only serves a
build if one exists, and says plainly when it does not.

**THE API BASE IS INJECTED RATHER THAN GUESSED.** `index.html` gets one meta tag
naming the origin it was served from, which `ConfigManager` reads before
anything else. The bundle stops carrying a hard-coded port, and moving the API
stops meaning a rebuild.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

AppRouter = APIRouter()

# `web/dist` relative to the repository root, which is two parents up from this
# file's package. Resolved once so a missing build is a clear message rather
# than a 404 per asset.
DIST = Path(__file__).resolve().parent.parent.parent / "web" / "dist"

BUILD_COMMAND = "cd web && npm install && npm run build"

# Injected into the served page. The name is read by `state/config_manager.ts`,
# which prefers it over every other way of finding the API.
META = '<meta name="codecarto-api" content="{origin}"/>'


def build_present() -> bool:
    """Whether a built application is on disk."""
    return (DIST / "index.html").is_file()


def _with_api_origin(html: str, origin: str) -> str:
    """`index.html`, told where its API is.

    Inserted after `<head>` rather than appended, so it is parsed before the
    module script that reads it. A meta tag after the bundle would be a tag the
    bundle never saw.
    """
    tag = META.format(origin=origin.rstrip("/"))
    if 'name="codecarto-api"' in html:
        return re.sub(r'<meta name="codecarto-api"[^>]*/?>', tag, html, count=1)
    return html.replace("<head>", f"<head>\n    {tag}", 1)


@AppRouter.get("/app", response_class=HTMLResponse, include_in_schema=False)
@AppRouter.get("/app/", response_class=HTMLResponse, include_in_schema=False)
async def application(request: Request) -> str:
    """The built application, or a sentence saying there is not one."""
    if not build_present():
        # **NOT A 404.** A missing build is a thing somebody can fix in one
        # command, and a bare 404 does not say which command or that a
        # development server is the other option.
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<title>Code Cartographer &mdash; not built</title>
<style>
 body {{ background:#0a0a0a; color:#00ff41; font:15px/1.6 ui-monospace,monospace;
   margin:0; padding:3rem 1.5rem; }}
 .box {{ max-width:44rem; margin:0 auto; }}
 code {{ background:#1a1a1a; padding:.15em .45em; border-radius:2px;
   color:#00d4ff; }}
 p {{ margin:0 0 1rem; }} .m {{ color:#00aa2a; }}
</style></head><body><div class="box">
<h1>The application is not built</h1>
<p>The API is running and answering &mdash; this is only about the page.</p>
<p>Build it once: <code>{BUILD_COMMAND}</code></p>
<p class="m">Or run the development server instead, which rebuilds as you
edit: <code>cd web &amp;&amp; npm run dev</code>. It serves on its own port and
talks to this API across origins.</p>
<p class="m">Looked in <code>{DIST}</code>.</p>
</div></body></html>"""

    html = (DIST / "index.html").read_text(encoding="utf-8")
    return _with_api_origin(html, str(request.base_url))
