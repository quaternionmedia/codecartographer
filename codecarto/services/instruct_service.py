"""Relaying an instruction a person typed in the window to the harness.

The harness records an instruction and runs nothing: acting on one is a
separate request that asks consent first. This module sends the text and, when
stated, the project to `POST /v1/instructions` with `page` as the way in, and
returns the row the harness made or the harness's refusal in its own words. It
keeps nothing, checks nothing the harness checks, and never sends twice.

`standing` decides whether a request may be relayed at all. The window names
nobody, so it relays only for a person at the machine the harness runs on: the
request arrived on a loopback address from a loopback address, carries no
header a proxy adds, and, when a browser says which page sent it, that page
was served from a loopback name. Anything else is told where an instruction
is given instead.

What `standing` cannot see: a proxy on this machine that adds no forwarding
header, and who is sitting at the keyboard.
"""

from __future__ import annotations

import ipaddress
from typing import Any, Mapping
from urllib.parse import urlsplit

from codecarto.services import qmcp_client

WAY_IN = "page"
"""The harness's name for an instruction that arrived from a page."""

TERMINAL = 'qmcp instruct "<what should be done>"'

FORWARDED = ("forwarded", "x-forwarded-for", "x-forwarded-host", "x-real-ip")
"""Headers a proxy adds. One of them means the sender is not the peer."""

ROUTE = "/harness/instructions"


def is_loopback(host: str | None) -> bool:
    """Whether a host, as a server scope or a URL names it, is this machine."""
    if not host:
        return False
    name = host.strip("[]").lower()
    if name == "localhost":
        return True
    try:
        return ipaddress.ip_address(name).is_loopback
    except ValueError:
        return False


def standing(server: str | None, client: str | None,
             headers: Mapping[str, str]) -> str:
    """Why this request may not be relayed, or "" when it may."""
    if not is_loopback(server):
        return "this window is being served on an address other than this machine's own"
    if not is_loopback(client):
        return "the request came from another machine"
    lowered = {key.lower(): value for key, value in headers.items()}
    for header in FORWARDED:
        if header in lowered:
            return f"the request passed through a proxy (it carries `{header}`)"
    origin = lowered.get("origin")
    if origin is not None and not is_loopback(urlsplit(origin).hostname):
        return "the page that sent the request was not served from this machine"
    return ""


def availability(why: str) -> dict[str, Any]:
    """Whether the window relays an instruction for this request, as a document."""
    if not why:
        return {"available": True, "way_in": WAY_IN, "problem": "", "remedy": "",
                "where": ROUTE}
    return _refused(f"an instruction is not taken here: {why}")


def _refused(problem: str, remedy: str = f"give it in a terminal: `{TERMINAL}`",
             where: str = ROUTE) -> dict[str, Any]:
    return {"available": False, "refused": True, "problem": problem,
            "remedy": remedy, "where": where}


def record(text: str, project: str | None, why: str) -> dict[str, Any]:
    """Send one instruction, and return the harness's row or why there is none.

    `why` is `standing`'s answer for the request being served. Text that is
    blank is not sent: the harness would refuse it, and the sentence here says
    what to type. Every other judgement is the harness's.
    """
    if why:
        return availability(why)
    said = (text or "").strip()
    if not said:
        return _refused("there is no instruction to record: the text is blank",
                        remedy="type what should be done")
    payload: dict[str, Any] = {"text": said, "source": WAY_IN}
    stated = (project or "").strip()
    if stated:
        payload["project"] = stated
    reach = qmcp_client.send("/v1/instructions", payload,
                             remedy_404=qmcp_client.LOOPBACK_ONLY)
    if reach.ok:
        return {"recorded": True, "instruction": reach.document, "where": reach.where}
    if reach.status is None:
        return {"unreachable": True, "problem": reach.problem,
                "remedy": reach.remedy, "where": reach.where}
    return _refused(reach.problem, remedy=reach.remedy, where=reach.where)
