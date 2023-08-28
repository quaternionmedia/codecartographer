import os


def get_appdata_dir() -> str:
    """Return the application data directory."""
    if os.name == "nt":
        # On Windows, use %APPDATA% environment variable
        return os.getenv("APPDATA")
    elif os.name == "posix":
        # On Linux/Unix/Mac, use ~/.local/share directory
        return os.path.expanduser("~/.local/share")
    else:
        # Unsupported operating system
        raise RuntimeError("Unsupported operating system.")


def get_codecarto_appdata_dir() -> str:
    """Return the C:\\Users\\USER\\AppData\Roaming\CodeCartographer directory."""
    codecarto_appdata_dir = os.path.join(get_appdata_dir(), "CodeCartographer")
    if not os.path.exists(codecarto_appdata_dir):
        os.makedirs(codecarto_appdata_dir, exist_ok=True)
    return codecarto_appdata_dir


APPDATA_DIRECTORY = get_appdata_dir()
CODECARTO_APPDATA_DIRECTORY = get_codecarto_appdata_dir()
