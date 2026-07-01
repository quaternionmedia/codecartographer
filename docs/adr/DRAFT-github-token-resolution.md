# ADR-XXXX — GitHub token resolution order: gh CLI keyring primary, env vars secondary

| | |
|---|---|
| **Status** | Proposed |
| **Date** | 2026-06-30 |
| **Pends on** | Integration test: verify `gh auth status` reports the keyring account as active after the fix |

## Context

`github_service.py`'s `create_headers()` read `GITHUB_TOKEN` first. The
`gh` CLI also reads `GITHUB_TOKEN` first when resolving credentials. The
result: a stale or expired `GITHUB_TOKEN` env var shadowed a valid
`gh` keyring credential at every level simultaneously — neither the
backend's `httpx` calls nor the `gh pr create` CLI command could reach
GitHub, even with `gh auth login` confirmed and a valid keyring token
present. `gh auth status` reported:

```
X Failed to log in to github.com using token (GITHUB_TOKEN)
  - Active account: true          # <- the bad env var is "active"

✓ Logged in to github.com account subcontrabass (keyring)
  - Active account: false         # <- the good keyring token is inactive
```

The same carousel recurred multiple times during this project's history
because clearing a system env var is not durable — it must be re-cleared
in every new shell session.

## Decision

Introduce `resolve_github_token()` in `github_service.py`, called once
at startup and cached. The resolution order is:

1. **`CC_GITHUB_TOKEN` env var** — project-specific override. Using a
   namespaced variable avoids any conflict with system-level or CI
   `GITHUB_TOKEN` variables set for other tooling.

2. **`gh auth token --hostname github.com`** (keyring) — `gh` is invoked
   in a subprocess with `GITHUB_TOKEN` and `GH_TOKEN` stripped from its
   environment, so it uses the keyring credential rather than the (possibly
   stale) env var. Timeout is 5 s; if `gh` is not installed this source
   is skipped silently.

3. **`GITHUB_TOKEN` / `GH_TOKEN` env vars** — legacy / Docker Compose
   pass-through. Still supported, but now at lower priority so a bad value
   does not shadow a valid keyring token.

4. **Docker secret** — `/run/secrets/github_token`.

5. **Unauthenticated** — 60 req/h per IP; logs a warning at startup.

`get_github_token()` returns the cached result; `create_headers()` calls
it. `repo_router.py`'s direct `os.environ.get("GITHUB_TOKEN")` call is
replaced with `get_github_token()` to close a second bypass path.

A `GET /auth/github` endpoint returns `{source, authenticated, token_prefix}`
so the current resolution is inspectable without reading server logs. The
frontend header shows a coloured GH indicator (green = authenticated,
amber = unauthenticated) with a tooltip naming the source.

## Consequences

- Developers who `gh auth login` and do nothing else get authenticated
  API access automatically. The "carousel of env vars" described in the
  project history is eliminated for local dev.
- Docker Compose and CI still work: set `CC_GITHUB_TOKEN` (preferred) or
  `GITHUB_TOKEN` (legacy); both are resolved in the expected way without
  `gh` installed.
- Token caching at module level means a token that expires mid-run will
  produce 401s until the process is restarted. The existing `_api_get`
  retry (strips auth and retries on 401) prevents hard failures for public
  repos — private repos would fail until restart. This is accepted: tokens
  typically last 8 h–1 year; a restart is the expected recovery.
- `gh` must be on `PATH` for source 2 to activate. If `gh` is absent,
  resolution falls through to env vars. No new hard dependency.

## Alternatives considered

1. **Fix by deleting `GITHUB_TOKEN` from the shell environment** — not
   durable; the problem recurs in every new shell session or after a
   system update sets the variable again.
2. **Replace all `httpx` GitHub calls with `gh api` subprocess calls** —
   `gh` handles auth automatically and completely; rejected as too invasive
   for this codebase's async architecture (blocking subprocess per API call
   inside async routes).
3. **Validate `GITHUB_TOKEN` against `/user` before using it** — adds
   an extra network round-trip on every startup even when the token is
   good; the keyring-first approach avoids the bad token entirely rather
   than detecting it after the fact.

## Revision triggers

- The token expiry / mid-run 401 failure rate becomes a real complaint
  (e.g., from long-running server deployments) — implement a background
  refresh or a cache TTL with re-resolution.
- A second VCS host (GitLab, Bitbucket) is supported — generalize
  `resolve_github_token()` into a per-host resolver.
- `gh` auth token output format changes — watch for `gh` major version
  bumps.

## Amendments

*None.*
