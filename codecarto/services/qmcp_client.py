"""Reaching the harness, and saying so plainly when it is not there.

**THIS IS THE SEAM.** `codecarto` does not import `qmcp` and cannot: they are
separate repositories with separate environments. It fetches a document over
HTTP and draws it. Everything this module knows about the harness is a URL and
the shape of a JSON payload.

**A HARNESS THAT IS NOT RUNNING IS THE ORDINARY CASE, NOT AN ERROR.** Somebody
opening this page has very often not started the harness yet -- it is a separate
process on a separate port. So a refused connection produces a `Reach` carrying
the reason and the command that fixes it, and the page renders that sentence.
A stack trace would be accurate and useless, and a blank graph would be worse
than either: it looks like an answer.

**THE FAILURES ARE KEPT APART.** Not running, running but too old to have the
route, running and refusing, and answering with something unreadable are four
different problems with four different fixes, and a single "could not load"
sends a reader to look in the wrong place.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

# e, for the front end; pi for the harness. A memory aid, not a claim -- both
# are overridable and nothing depends on the digits.
DEFAULT_BASE = "http://127.0.0.1:3141"

TIMEOUT = 6.0
"""Seconds. Short on purpose: this sits in front of a page render, and a
front end that hangs is worse than one that says the harness is slow."""

START_COMMAND = "uv run qm dashboard --start harness"


def base_url() -> str:
    """Where the harness is, with the environment winning."""
    return (os.environ.get("QMCP_URL") or DEFAULT_BASE).rstrip("/")


@dataclass
class Reach:
    """What came back, or why nothing did."""

    ok: bool
    where: str
    document: dict[str, Any] = field(default_factory=dict)
    problem: str = ""
    remedy: str = ""
    """What the reader can actually do. Empty when there is nothing they
    could do, which is itself worth not pretending about."""

    status: int | None = None


def fetch(path: str, base: str | None = None) -> Reach:
    """One document from the harness.

    Never raises. A front end that threw on a missing harness would turn "not
    started yet" into a 500, and the page would report a fault in itself.
    """
    where = f"{base or base_url()}{path}"
    request = urllib.request.Request(where, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:
            body = answer.read()
            return Reach(True, where, json.loads(body), status=answer.status)
    except urllib.error.HTTPError as error:
        detail = _detail(error)
        if error.code == 404:
            return Reach(
                False, where, status=404,
                problem=(f"the harness is running and has no {path}. "
                         f"{detail}" if detail else
                         f"the harness is running but does not serve {path}"),
                remedy=("this build of the harness predates the topology "
                        "routes, or the archive it needs has not been indexed"))
        return Reach(False, where, status=error.code,
                     problem=f"the harness refused: {error.code} {detail}",
                     remedy="")
    except urllib.error.URLError as error:
        return Reach(
            False, where,
            problem=f"nothing is answering at {base or base_url()}",
            remedy=f"start it with `{START_COMMAND}`",
            status=None)
    except (TimeoutError, OSError) as error:
        return Reach(False, where,
                     problem=f"the harness did not answer within {TIMEOUT:g}s",
                     remedy="", status=None)
    except json.JSONDecodeError:
        return Reach(False, where,
                     problem="the harness answered with something that is not "
                             "JSON",
                     remedy="", status=None)


def _detail(error: urllib.error.HTTPError) -> str:
    """The harness's own explanation, which is better than any this can write."""
    try:
        return str(json.loads(error.read()).get("detail", ""))
    except Exception:                              # noqa: BLE001
        return ""


def topologies(base: str | None = None) -> Reach:
    """Every topology the harness knows, with the encoding."""
    return fetch("/v1/topology", base)


def shape(kind: str, level: int = 2, base: str | None = None) -> Reach:
    """One topology, at a resolution."""
    return fetch(f"/v1/topology/shape/{kind}?level={level}", base)


def relations(subject: str, base: str | None = None) -> Reach:
    """What the archive says one project is related to.

    Loopback-only at the harness, so this is a 404 from anywhere else -- which
    is the harness's decision and not this side's to route around.
    """
    return fetch(f"/v1/topology/relations/{subject}", base)
