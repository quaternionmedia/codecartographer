# Gravis pkg_resources Deprecation Warning

**Date**: 2026-01-17
**Status**: ⚠️ Warning (Non-blocking)
**Severity**: Low (Will become critical after 2025-11-30)

## Warning Message

```
C:\Users\peter\repos\codecartographer\.venv\Lib\site-packages\gravis\_internal\plotting\template_system.py:5:
UserWarning: pkg_resources is deprecated as an API.
See https://setuptools.pypa.io/en/latest/pkg_resources.html.
The pkg_resources package is slated for removal as early as 2025-11-30.
Refrain from using this package or pin to Setuptools<81.
```

## Root Cause

The `gravis` library (used for graph visualization in the backend) is using the deprecated `pkg_resources` module from `setuptools`. This is a third-party dependency issue.

**Affected File**: `gravis/_internal/plotting/template_system.py:5`

## Impact

- **Current**: Warning only, no functional impact
- **Future**: After November 30, 2025, `pkg_resources` will be removed from setuptools
- **Result**: Gravis will break unless:
  1. Gravis updates to use `importlib.resources` or `importlib.metadata`
  2. We pin setuptools to version <81
  3. We replace gravis with an alternative

## Recommended Solutions

### Option 1: Pin Setuptools (Short-term fix)

Add to `pyproject.toml`:

```toml
[project]
dependencies = [
    "gravis>=0.1.0",
    "setuptools<81",  # Pin until gravis updates
    # ... other deps
]
```

**Pros**:
- Immediate fix
- No code changes required

**Cons**:
- Blocks setuptools updates
- Not a long-term solution

### Option 2: Wait for Gravis Update (Recommended)

Monitor gravis repository for updates:
- Repository: https://github.com/robert-haas/gravis
- Check for issues/PRs addressing pkg_resources deprecation
- Update gravis when fixed

**Pros**:
- Proper fix from upstream
- No maintenance burden

**Cons**:
- Depends on gravis maintainer
- May take time

### Option 3: Migrate Away from Gravis (Long-term)

We're already using D3.js on the frontend, so backend graph serialization is minimal. Options:

1. **Use NetworkX directly** - We already have it
   ```python
   # Instead of gravis.convert.any_to_gjgf(graph)
   # Serialize NetworkX graph manually to gJGF format
   ```

2. **Use networkx.node_link_data()** - Built-in JSON serialization
   ```python
   import networkx as nx
   graph_json = nx.node_link_data(graph)
   # Convert to gJGF format if needed
   ```

3. **Custom serializer** - Full control
   ```python
   # We already created GraphSerializer in codecarto/services/graph_serializer.py
   # Can extend it to not depend on gravis
   ```

**Pros**:
- Remove dependency entirely
- Full control over serialization
- No external deprecation concerns

**Cons**:
- Requires code changes
- Need to maintain serialization logic

## Immediate Action Required

None - this is just a warning. The code still works.

## Recommended Timeline

1. **Now - Jan 2026**: Monitor only, no action needed
2. **Q2 2026**: Check gravis for updates
3. **Q3 2026**: If no gravis update, implement Option 1 (pin setuptools)
4. **Q4 2026**: Consider Option 3 (migrate away) as part of larger refactor

## Technical Details

### What is pkg_resources?

`pkg_resources` is part of setuptools and provides:
- Package metadata reading
- Resource file access
- Version parsing
- Entry point discovery

### Why is it deprecated?

Python 3.9+ introduced native alternatives:
- `importlib.metadata` - For package metadata
- `importlib.resources` - For resource files

These are faster, more reliable, and part of the standard library.

### How Gravis Uses It

Gravis likely uses `pkg_resources` to:
1. Load HTML/JS templates from package resources
2. Read package version
3. Access bundled static files

### Modern Alternative

```python
# OLD (pkg_resources)
import pkg_resources
template = pkg_resources.resource_string('gravis', 'templates/graph.html')

# NEW (importlib.resources)
from importlib.resources import files
template = files('gravis').joinpath('templates/graph.html').read_text()
```

## Monitoring

Check gravis repository periodically:
```bash
# Check current gravis version
uv pip show gravis

# Check for updates
uv pip index versions gravis

# Monitor GitHub
# https://github.com/robert-haas/gravis/issues
```

## Related Files

- [pyproject.toml](../../pyproject.toml) - Dependency management
- [codecarto/services/graph_serializer.py](../../codecarto/services/graph_serializer.py) - Uses gravis
- [codecarto/routers/plotter_router.py](../../codecarto/routers/plotter_router.py) - Uses graph_serializer

## References

- [Setuptools pkg_resources deprecation](https://setuptools.pypa.io/en/latest/pkg_resources.html)
- [importlib.resources documentation](https://docs.python.org/3/library/importlib.resources.html)
- [importlib.metadata documentation](https://docs.python.org/3/library/importlib.metadata.html)
- [Gravis GitHub](https://github.com/robert-haas/gravis)

---

**Status**: ⚠️ Warning only - Safe to ignore for now
**Action**: Monitor gravis updates, consider migration in future
**Deadline**: Before November 30, 2025
