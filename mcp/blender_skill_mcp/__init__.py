"""blender-skill MCP package.

Server imports are lazy so the installer can use ``paths`` with only the
standard library available.
"""

__all__ = ["create_server", "main"]
__version__ = "1.0.0"


def create_server(*args, **kwargs):
    from .server import create_server as _create

    return _create(*args, **kwargs)


def main(*args, **kwargs):
    from .server import main as _main

    return _main(*args, **kwargs)
