"""
Tests for codecarto.models.source_data.Folder.iter_files() — the shared
recursive (folder, file) traversal extracted so callers needing "every
file under this folder" don't each hand-roll their own recursive walk
(see docs/llm/next_steps/parser_consolidation_and_scope_drift.md, 1.4).
Used by _collect_parseable and _add_python_dependency_edges
(unified_parser_service.py) and _fetch_content_for_folder
(github_service.py).
"""

from codecarto.models.source_data import File, Folder


class TestFolderIterFiles:
    def test_empty_folder_yields_nothing(self):
        f = Folder(name="root", size=0, files=[], folders=[])
        assert list(f.iter_files()) == []

    def test_flat_files_yield_self_as_owning_folder(self):
        a = File(name="a.py")
        b = File(name="b.py")
        root = Folder(name="root", size=0, files=[a, b], folders=[])

        results = list(root.iter_files())

        assert results == [(root, a), (root, b)]

    def test_nested_files_yield_their_own_subfolder(self):
        nested = File(name="nested.py")
        sub = Folder(name="pkg", size=0, files=[nested], folders=[])
        top = File(name="top.py")
        root = Folder(name="root", size=0, files=[top], folders=[sub])

        results = list(root.iter_files())

        assert (root, top) in results
        assert (sub, nested) in results
        assert len(results) == 2

    def test_deeply_nested_folders_all_visited(self):
        f3 = File(name="deep.py")
        level3 = Folder(name="level3", size=0, files=[f3], folders=[])
        level2 = Folder(name="level2", size=0, files=[], folders=[level3])
        level1 = Folder(name="level1", size=0, files=[], folders=[level2])
        root = Folder(name="root", size=0, files=[], folders=[level1])

        results = list(root.iter_files())

        assert results == [(level3, f3)]

    def test_multiple_subfolders_all_visited(self):
        fa = File(name="a.py")
        fb = File(name="b.py")
        sub_a = Folder(name="a", size=0, files=[fa], folders=[])
        sub_b = Folder(name="b", size=0, files=[fb], folders=[])
        root = Folder(name="root", size=0, files=[], folders=[sub_a, sub_b])

        results = list(root.iter_files())

        assert set(f.name for _, f in results) == {"a.py", "b.py"}
        owning_names = {owner.name for owner, _ in results}
        assert owning_names == {"a", "b"}
