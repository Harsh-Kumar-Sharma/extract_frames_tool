"""CVAT upload archive creation."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def create_cvat_zip(output: Path, include_metadata: bool = False) -> Path:
    """Create an archive with images at its root and optional metadata folder."""
    target = output / "cvat_upload.zip"
    temporary = output / "cvat_upload.zip.tmp"
    try:
        with ZipFile(temporary, "w", ZIP_DEFLATED, allowZip64=True) as archive:
            for image in sorted((output / "images").iterdir()):
                if image.is_file():
                    archive.write(image, image.name)
            if include_metadata:
                for item in sorted((output / "metadata").iterdir()):
                    if item.is_file():
                        archive.write(item, f"metadata/{item.name}")
        temporary.replace(target)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise
    return target
