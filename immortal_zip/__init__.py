"""Immortal-Zip: zip, unzip, and repair corrupted zip archives."""

from .core import ZipTool, RepairResult, ZipError

__version__ = "1.0.0"
__all__ = ["ZipTool", "RepairResult", "ZipError", "__version__"]
