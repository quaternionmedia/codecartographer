# Contributing Guide

Guidelines for contributing to Codecarto.

---

## Development Setup

### Prerequisites

- Python 3.10+
- UV package manager
- Node.js 18+
- Git

### Clone and Install

```bash
git clone https://github.com/quaternionmedia/codecartographer.git
cd codecartographer
git submodule init && git submodule update

uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -e ".[dev]"
```

### Verify Setup

```bash
uv run codecarto info
uv run codecarto --version
```

---

## Development Workflow

### 1. Start Development Environment

```bash
uv run codecarto dev
```

### 2. Make Changes

Edit files in `codecarto/` - hot reload is enabled.

### 3. Test Changes

```bash
# Run linter
uv run codecarto lint

# Auto-fix lint issues
uv run codecarto lint --fix

# Run tests (when implemented)
uv run pytest
```

### 4. Commit Changes

```bash
git add .
git commit -m "feat: add new feature"
```

---

## Code Style

### Python

- **Formatter:** Ruff (configured in `pyproject.toml`)
- **Line length:** 100 characters
- **Target:** Python 3.10+

```bash
# Check style
uv run codecarto lint

# Auto-fix
uv run codecarto lint --fix
```

### Ruff Configuration

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "W"]
ignore = ["E501"]
```

### Import Order

```python
# Standard library
import os
import sys

# Third-party
from fastapi import APIRouter
import networkx as nx

# Local
from codecarto.models.source_data import Directory
from codecarto.services.parser_service import ParserService
```

---

## Project Structure

### Adding a New Feature

```
1. Model (if needed)     → codecarto/models/
2. Service (logic)       → codecarto/services/
3. Router (API endpoint) → codecarto/routers/
4. CLI command (if needed) → codecarto/cli.py
5. Tests                 → tests/
6. Documentation         → docs/
```

### Example: Adding a New Graph Type

```python
# 1. Create parser: services/parsers/my_parser.py
class MyParser:
    def parse(self, directory):
        graph = nx.DiGraph()
        # Build graph
        return graph

# 2. Add to ParserService: services/parser_service.py
@staticmethod
async def parse_my_type(directory: Directory) -> nx.DiGraph:
    parser = MyParser()
    graph = parser.parse(directory)
    return graph

# 3. Add API endpoint: routers/local_repo_router.py
@LocalRepoRouter.get("/graph/my_type")
async def get_my_type_graph(path: str):
    directory = get_local_repo(path)
    graph = await ParserService.parse_my_type(directory)
    # Return response

# 4. Add CLI command: cli.py
# Update the repo graph command to include new type
```

---

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Code style (no logic change) |
| `refactor` | Code refactoring |
| `test` | Add/update tests |
| `chore` | Maintenance tasks |

### Examples

```
feat(cli): add local repo scan command
fix(parser): handle empty files gracefully
docs(api): add endpoint documentation
refactor(services): extract common parsing logic
```

---

## Testing

### Running Tests

```bash
uv run pytest
uv run pytest -v                    # Verbose
uv run pytest tests/test_parser.py  # Specific file
uv run pytest -k "test_scan"        # Pattern match
```

### Writing Tests

```python
# tests/test_local_repo.py

import pytest
from codecarto.services.local_repo_service import get_local_repo

def test_scan_directory(tmp_path):
    # Create test file
    test_file = tmp_path / "test.py"
    test_file.write_text("def hello(): pass")
    
    # Test scan
    result = get_local_repo(str(tmp_path))
    
    assert result.info.name == tmp_path.name
    assert len(result.root.files) == 1

@pytest.mark.asyncio
async def test_async_operation():
    # Async test example
    result = await some_async_function()
    assert result is not None
```

---

## Documentation

### Updating Docs

Documentation lives in `docs/`:

```
docs/
├── index.md           # Entry point
├── getting-started.md # Installation
├── cli.md             # CLI reference
├── api.md             # API reference
├── architecture.md    # System design
├── services.md        # Service docs
└── contributing.md    # This file
```

### Documentation Style

- Use Markdown
- Include code examples
- Keep it concise
- Update when changing features

---

## Pull Request Process

### 1. Create Branch

```bash
git checkout -b feat/my-feature
```

### 2. Make Changes

- Write code
- Add tests
- Update docs

### 3. Validate

```bash
uv run codecarto lint
uv run pytest
```

### 4. Push and Create PR

```bash
git push origin feat/my-feature
```

Then create PR on GitHub.

### PR Checklist

- [ ] Code follows style guide
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] No merge conflicts

---

## Architecture Decisions

### Why UV?

- Fast dependency resolution
- Modern Python packaging
- Reproducible environments
- Single tool for venv + pip

### Why Click for CLI?

- Composable command groups
- Automatic help generation
- Type validation
- Easy testing

### Why FastAPI?

- Automatic OpenAPI docs
- Async support
- Pydantic integration
- Performance

### Why NetworkX?

- Mature graph library
- Rich algorithms
- Easy serialization
- Good visualization support

---

## Getting Help

- **Issues:** [GitHub Issues](https://github.com/quaternionmedia/codecartographer/issues)
- **Discussions:** GitHub Discussions
- **Documentation:** `docs/` folder

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
