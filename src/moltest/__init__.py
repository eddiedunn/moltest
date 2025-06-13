# moltest/__init__.py
try:
    from importlib.metadata import version
except ImportError:
    from importlib_metadata import version  # type: ignore

__version__ = version("moltest")
