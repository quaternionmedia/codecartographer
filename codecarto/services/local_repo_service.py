"""
Local repository service for parsing local git repositories.
"""
import os
from pathlib import Path
from typing import Optional, List
from codecarto.models.source_data import Directory, File, Folder, RepoInfo

# Cap raw file content at 1 MB; bigger files keep raw='' and rely on
# parsers that read from disk (e.g. libclang via CLangaugeParser).
_MAX_RAW_BYTES = 1_000_000


def get_local_repo(
    path: str,
    extensions: Optional[List[str]] = None,
    exclude_dirs: Optional[List[str]] = None
) -> Directory:
    """
    Read a local directory/repo and build a Directory structure.

    Args:
        path:        Path to the local repository.
        extensions:  File extensions to include (e.g. ['.py', '.cs']).
                     If None, all extensions registered with ParserRegistry are included.
        exclude_dirs: Directory names/globs to skip.

    Returns:
        Directory object with the repo structure.
    """
    if extensions is None:
        extensions = _default_extensions()

    # Normalize: lowercase, ensure leading dot
    extensions = [e.lower() if e.startswith('.') else f'.{e.lower()}' for e in extensions]

    if exclude_dirs is None:
        exclude_dirs = [
            '.git', '.venv', 'venv', '__pycache__',
            'node_modules', '.pytest_cache', '.mypy_cache',
            'dist', 'build', '.eggs', '*.egg-info',
            '.vs', '.idea', '.vscode',
            'bin', 'obj', # .NET build output
        ]
    
    repo_path = Path(path).resolve()
    
    if not repo_path.exists():
        raise FileNotFoundError(f"Path does not exist: {repo_path}")
    
    if not repo_path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {repo_path}")
    
    # Detect repo name and owner from git or path
    repo_name = repo_path.name
    owner = _get_git_owner(repo_path) or "local"
    
    # Build the folder structure
    root = _build_folder_tree(repo_path, extensions, exclude_dirs)
    root.name = repo_name
    
    return Directory(
        info=RepoInfo(owner=owner, name=repo_name, url=str(repo_path)),
        size=root.size,
        root=root,
        is_partial=False,
    )


def _get_git_owner(repo_path: Path) -> Optional[str]:
    """Try to extract owner from git remote URL."""
    git_config = repo_path / ".git" / "config"
    if not git_config.exists():
        return None
    
    try:
        content = git_config.read_text()
        
        # Look for remote origin URL patterns:
        # https://github.com/owner/repo.git
        # git@github.com:owner/repo.git
        import re
        
        # Try HTTPS URL first
        match = re.search(r'url\s*=\s*https://[^/]+/([^/]+)/([^/\s]+?)(?:\.git)?(?:\s|$)', content)
        if match:
            return match.group(1)
        
        # Try SSH URL
        match = re.search(r'url\s*=\s*git@[^:]+:([^/]+)/([^/\s]+?)(?:\.git)?(?:\s|$)', content)
        if match:
            return match.group(1)
    except Exception:
        pass
    
    return None


def _build_folder_tree(
    folder_path: Path,
    extensions: List[str],
    exclude_dirs: List[str]
) -> Folder:
    """
    Recursively build a Folder tree from a local directory.
    """
    files: List[File] = []
    folders: List[Folder] = []
    total_size = 0
    
    try:
        entries = sorted(folder_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
    except PermissionError:
        return Folder(name=folder_path.name, size=0, files=[], folders=[])
    
    for entry in entries:
        # Skip excluded directories
        if entry.is_dir():
            if _should_exclude(entry.name, exclude_dirs):
                continue
            
            sub_folder = _build_folder_tree(entry, extensions, exclude_dirs)
            sub_folder.name = entry.name
            folders.append(sub_folder)
            total_size += sub_folder.size
            continue
        
        # Skip if this is not a file
        if not entry.is_file():
            continue

        # Skip files that don't match the specified extensions
        if extensions and entry.suffix.lower() not in extensions:
            continue
    
        # Read file content for Python files
        try:
            file_size = entry.stat().st_size
            raw = _read_text_capped(entry, file_size)
            files.append(File(
                url=str(entry), # disk path — libclang and other on-disk parsers use this
                name=entry.name,
                size=file_size,
                raw=raw,        # source text for parsers that need it; '' if too large or unreadable
            ))
            total_size += file_size
        except (PermissionError, OSError):
            continue
    
    return Folder(
        name=folder_path.name,
        size=total_size,
        files=files,
        folders=folders
    )


def _read_text_capped(file_path: Path, file_size: int) -> str:
    """Read file as UTF-8 text, returning '' on decode errors or oversize files."""
    if file_size > _MAX_RAW_BYTES:
        return ''
    try:
        return file_path.read_text(encoding='utf-8')
    except (UnicodeDecodeError, PermissionError, OSError):
        return ''


def _default_extensions() -> List[str]:
    """All extensions registered with the unified ParserRegistry.

    Resolved lazily so this module doesn't import parsers at module-load time.
    """
    from codecarto.services.parsers.language_parser import ParserRegistry
    return list(ParserRegistry.all_extensions())


def _should_exclude(name: str, exclude_patterns: List[str]) -> bool:
    """Check if a directory name matches any exclude pattern."""
    import fnmatch
    return any(fnmatch.fnmatch(name, p) for p in exclude_patterns)


def get_file_stats(directory: Directory) -> dict:
    """Get statistics about files in the directory."""
    stats = {
        "total_files": 0,
        "total_size": directory.size,
        "python_files": 0,
        "folders": 0,
    }
    
    def count_folder(folder: Folder):
        stats["total_files"] += len(folder.files)
        stats["python_files"] += sum(1 for f in folder.files if f.name.endswith('.py'))
        stats["folders"] += len(folder.folders)
        for sub in folder.folders:
            count_folder(sub)
    
    count_folder(directory.root)
    return stats
