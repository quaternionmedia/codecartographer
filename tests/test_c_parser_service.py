"""
Tests for codecarto.services.c_parser_service.CParserService

These tests focus on the service layer: path validation, error wrapping,
and graceful handling of missing libclang. The libclang integration itself
requires system-level LLVM libraries and is exercised in manual / CI tests.
"""

import pytest
from codecarto.util.exceptions import CodeCartoException


class TestCParserServicePathValidation:
    """parse_file and parse_directory should raise CodeCartoException for bad paths."""

    def test_parse_file_missing_raises(self, tmp_path):
        from codecarto.services.c_parser_service import CParserService

        with pytest.raises(CodeCartoException) as exc_info:
            CParserService.parse_file(str(tmp_path / "nonexistent.c"))

        exc = exc_info.value
        assert exc.status_code == 404
        assert "not found" in exc.message.lower()

    def test_parse_directory_missing_raises(self, tmp_path):
        from codecarto.services.c_parser_service import CParserService

        missing = tmp_path / "no_such_dir"
        with pytest.raises(CodeCartoException) as exc_info:
            CParserService.parse_directory(str(missing))

        exc = exc_info.value
        assert exc.status_code == 404

    def test_parse_directory_empty_dir_raises(self, tmp_path):
        from codecarto.services.c_parser_service import CParserService

        with pytest.raises(CodeCartoException) as exc_info:
            CParserService.parse_directory(str(tmp_path))

        exc = exc_info.value
        # "No .c or .h files found"
        assert exc.status_code == 404

    def test_parse_compile_commands_missing_raises(self, tmp_path):
        from codecarto.services.c_parser_service import CParserService

        with pytest.raises(CodeCartoException) as exc_info:
            CParserService.parse_directory(
                str(tmp_path),
                compile_commands=str(tmp_path / "missing_cc.json"),
            )

        exc = exc_info.value
        assert exc.status_code == 404


class TestCParserServiceImportError:
    """Without libclang installed, CParserService should raise CodeCartoException
    wrapping the ImportError — not propagate a raw ImportError."""

    def test_parse_file_wraps_import_error_when_libclang_missing(self, tmp_path, monkeypatch):
        from codecarto.services.c_parser_service import CParserService

        # Create a real C file so path validation passes
        c_file = tmp_path / "hello.c"
        c_file.write_text("int main() { return 0; }\n")

        # Simulate libclang not being installed
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "clang.cindex" or name == "clang":
                raise ImportError("No module named 'clang'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        # Also reset the cached index so lazy-init runs again
        import codecarto.services.parsers.c_parser as c_parser_mod
        original_idx = c_parser_mod._clang_idx
        c_parser_mod._clang_idx = None

        try:
            with pytest.raises(CodeCartoException) as exc_info:
                CParserService.parse_file(str(c_file))
            assert "libclang" in exc_info.value.message.lower() or "clang" in exc_info.value.message.lower()
        finally:
            c_parser_mod._clang_idx = original_idx
