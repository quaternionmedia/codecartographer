"""
Tests for codecarto.services.local_repo_service.get_local_repo

Covers the local-directory-path-hookup behavior: default extensions now
come from ParserRegistry (not just .py), extension normalization, the new
exclude_dirs entries, raw-content capping/decoding, and is_partial=False.
"""

import pytest

from codecarto.services.local_repo_service import get_local_repo, get_file_stats


class TestGetLocalRepoPathValidation:
    def test_missing_path_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            get_local_repo(str(tmp_path / "does_not_exist"))

    def test_file_instead_of_dir_raises_not_a_directory(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("hello")
        with pytest.raises(NotADirectoryError):
            get_local_repo(str(f))


class TestGetLocalRepoDefaultExtensions:
    def test_default_extensions_include_non_python_registered_languages(self, tmp_path):
        (tmp_path / "main.py").write_text("print('hi')\n")
        (tmp_path / "lib.c").write_text("int main() { return 0; }\n")
        (tmp_path / "notes.txt").write_text("not a registered extension\n")

        directory = get_local_repo(str(tmp_path))

        names = {f.name for f in directory.root.files}
        assert "main.py" in names
        assert "lib.c" in names
        assert "notes.txt" not in names

    def test_explicit_extensions_normalize_case_and_missing_dot(self, tmp_path):
        (tmp_path / "main.PY").write_text("print('hi')\n")
        (tmp_path / "app.js").write_text("console.log('hi')\n")
        (tmp_path / "skip.rb").write_text("puts 'hi'\n")

        directory = get_local_repo(str(tmp_path), extensions=["PY", "js"])

        names = {f.name for f in directory.root.files}
        assert names == {"main.PY", "app.js"}


class TestGetLocalRepoExcludeDirs:
    def test_default_exclude_dirs_skip_new_entries(self, tmp_path):
        for d in [".vs", ".idea", ".vscode", "bin", "obj", "node_modules"]:
            sub = tmp_path / d
            sub.mkdir()
            (sub / "file.py").write_text("x = 1\n")
        (tmp_path / "keep.py").write_text("x = 1\n")

        directory = get_local_repo(str(tmp_path))

        folder_names = {f.name for f in directory.root.folders}
        assert folder_names == set()
        assert {f.name for f in directory.root.files} == {"keep.py"}

    def test_custom_exclude_dirs_override_default(self, tmp_path):
        sub = tmp_path / "custom_exclude"
        sub.mkdir()
        (sub / "file.py").write_text("x = 1\n")
        (tmp_path / "keep.py").write_text("x = 1\n")

        directory = get_local_repo(str(tmp_path), exclude_dirs=["custom_exclude"])

        folder_names = {f.name for f in directory.root.folders}
        assert folder_names == set()


class TestGetLocalRepoRawContent:
    def test_small_file_reads_full_raw_content(self, tmp_path):
        (tmp_path / "main.py").write_text("x = 1\n")

        directory = get_local_repo(str(tmp_path))

        f = next(f for f in directory.root.files if f.name == "main.py")
        assert f.raw == "x = 1\n"

    def test_oversize_file_keeps_raw_empty(self, tmp_path):
        big = tmp_path / "big.py"
        big.write_text("x" * (1_000_001))

        directory = get_local_repo(str(tmp_path))

        f = next(f for f in directory.root.files if f.name == "big.py")
        assert f.raw == ""
        assert f.size == 1_000_001

    def test_undecodable_file_keeps_raw_empty_not_error_string(self, tmp_path):
        bad = tmp_path / "bad.py"
        bad.write_bytes(b"\xff\xfe\x00\x01invalid utf-8")

        directory = get_local_repo(str(tmp_path))

        f = next(f for f in directory.root.files if f.name == "bad.py")
        assert f.raw == ""


class TestGetLocalRepoMetadata:
    def test_is_partial_is_false(self, tmp_path):
        (tmp_path / "main.py").write_text("x = 1\n")
        directory = get_local_repo(str(tmp_path))
        assert directory.is_partial is False

    def test_owner_falls_back_to_local_without_git(self, tmp_path):
        (tmp_path / "main.py").write_text("x = 1\n")
        directory = get_local_repo(str(tmp_path))
        assert directory.info.owner == "local"

    def test_owner_parsed_from_https_git_remote(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text(
            '[remote "origin"]\n'
            "\turl = https://github.com/quaternionmedia/codecartographer.git\n"
        )
        (tmp_path / "main.py").write_text("x = 1\n")

        directory = get_local_repo(str(tmp_path))

        assert directory.info.owner == "quaternionmedia"

    def test_owner_parsed_from_ssh_git_remote(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text(
            '[remote "origin"]\n'
            "\turl = git@github.com:quaternionmedia/codecartographer.git\n"
        )
        (tmp_path / "main.py").write_text("x = 1\n")

        directory = get_local_repo(str(tmp_path))

        assert directory.info.owner == "quaternionmedia"

    def test_repo_name_is_directory_name(self, tmp_path):
        (tmp_path / "main.py").write_text("x = 1\n")
        directory = get_local_repo(str(tmp_path))
        assert directory.info.name == tmp_path.name
        assert directory.root.name == tmp_path.name


class TestGetLocalRepoNestedFolders:
    def test_nested_subfolder_included_with_size_rollup(self, tmp_path):
        sub = tmp_path / "pkg"
        sub.mkdir()
        (sub / "mod.py").write_text("x = 1\n")

        directory = get_local_repo(str(tmp_path))

        assert len(directory.root.folders) == 1
        sub_folder = directory.root.folders[0]
        assert sub_folder.name == "pkg"
        assert sub_folder.size > 0
        assert directory.root.size >= sub_folder.size


class TestGetFileStats:
    def test_counts_files_and_folders(self, tmp_path):
        sub = tmp_path / "pkg"
        sub.mkdir()
        (sub / "mod.py").write_text("x = 1\n")
        (tmp_path / "main.py").write_text("x = 1\n")
        (tmp_path / "lib.c").write_text("int main() { return 0; }\n")

        directory = get_local_repo(str(tmp_path))
        stats = get_file_stats(directory)

        assert stats["total_files"] == 3  # recurses into subfolders too
        assert stats["python_files"] == 2
        assert stats["folders"] == 1
