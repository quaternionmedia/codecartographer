"""
Local repository service for parsing local git repositories.
"""
import os
from pathlib import Path
from typing import Optional, List
from codecarto.models.source_data import Directory, File, Folder, RepoInfo


def get_local_repo(
    path: str,
    extensions: Optional[List[str]] = None,
    exclude_dirs: Optional[List[str]] = None
) -> Directory:
    """
    Read a local directory/repo and build a Directory structure.
    
    Args:
        path: Path to the local repository
        extensions: List of file extensions to include (e.g., ['.py']). 
                   If None, includes all files.
        exclude_dirs: List of directory names to exclude (e.g., ['.git', 'node_modules'])
    
    Returns:
        Directory object with the repo structure
    """
    if extensions is None:
        extensions = ['.py']  # Default to Python files
    
    if exclude_dirs is None:
        exclude_dirs = [
            '.git', '.venv', 'venv', '__pycache__', 
            'node_modules', '.pytest_cache', '.mypy_cache',
            'dist', 'build', '.eggs', '*.egg-info'
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
    )


def _get_git_owner(repo_path: Path) -> Optional[str]:
    """Try to extract owner from git remote URL."""
    git_config = repo_path / ".git" / "config"
    if not git_config.exists():
        return None
    
    try:
        with open(git_config, "r") as f:
            content = f.read()
        
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
        
        elif entry.is_file():
            # Check file extension
            if extensions and entry.suffix.lower() not in extensions:
                continue
            
            try:
                file_size = entry.stat().st_size
                
                # Read file content for Python files
                raw = ""
                if entry.suffix.lower() == '.py':
                    try:
                        with open(entry, "r", encoding="utf-8") as f:
                            raw = f.read()
                    except (UnicodeDecodeError, PermissionError):
                        raw = f"# Error reading file: {entry.name}"
                
                files.append(File(
                    url=str(entry),
                    name=entry.name,
                    size=file_size,
                    raw=raw
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


def _should_exclude(name: str, exclude_patterns: List[str]) -> bool:
    """Check if a directory name matches any exclude pattern."""
    import fnmatch
    
    for pattern in exclude_patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


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
