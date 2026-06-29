"""
Tests for codecarto.routers.repo_router — local-path branch of /repo/tree
and /repo/subtree.

Covers the "Hooked up local directory path parsing" merge: is_github_url
dispatches local filesystem paths to get_local_repo instead of the GitHub
API. The GitHub branch (network calls) is not exercised here.
"""

import pytest
from fastapi.testclient import TestClient

from codecarto.main import app


@pytest.fixture()
def client():
    return TestClient(app)


class TestRepoTreeLocalPath:
    def test_local_directory_returns_200(self, client, tmp_path):
        (tmp_path / "main.py").write_text("x = 1\n")

        resp = client.get("/repo/tree", params={"url": str(tmp_path)})

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == 200
        assert data["results"]["root"]["name"] == tmp_path.name

    def test_local_directory_lists_files(self, client, tmp_path):
        (tmp_path / "main.py").write_text("x = 1\n")
        (tmp_path / "lib.c").write_text("int main() { return 0; }\n")

        resp = client.get("/repo/tree", params={"url": str(tmp_path)})

        names = {f["name"] for f in resp.json()["results"]["root"]["files"]}
        assert names == {"main.py", "lib.c"}

    def test_missing_local_path_returns_500(self, client, tmp_path):
        resp = client.get("/repo/tree", params={"url": str(tmp_path / "missing")})

        # proc_exception always raises HTTPException(status_code=500, ...)
        # regardless of the underlying error — see codecarto/util/exceptions.py
        assert resp.status_code == 500
        assert "does not exist" in resp.json()["message"].lower()

    def test_does_not_treat_local_path_as_github_url(self, client, tmp_path, monkeypatch):
        import codecarto.routers.repo_router as repo_router

        async def fail_if_called(*args, **kwargs):
            raise AssertionError("get_raw_from_repo should not be called for a local path")

        monkeypatch.setattr(repo_router, "get_raw_from_repo", fail_if_called)
        (tmp_path / "main.py").write_text("x = 1\n")

        resp = client.get("/repo/tree", params={"url": str(tmp_path)})

        assert resp.status_code == 200
        assert resp.json()["status"] == 200


class TestRepoSubtreeLocalPath:
    def test_local_subtree_returns_subfolder(self, client, tmp_path):
        sub = tmp_path / "pkg"
        sub.mkdir()
        (sub / "mod.py").write_text("x = 1\n")

        resp = client.get("/repo/subtree", params={"url": str(tmp_path), "path": "pkg"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == 200
        assert data["results"]["name"] == "pkg"
        assert {f["name"] for f in data["results"]["files"]} == {"mod.py"}

    def test_local_subtree_missing_path_returns_500(self, client, tmp_path):
        resp = client.get(
            "/repo/subtree", params={"url": str(tmp_path), "path": "does_not_exist"}
        )

        assert resp.status_code == 500
