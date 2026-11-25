"""M2 bit-to-pixel mapping using the application's Pillow dependency."""

from io import BytesIO

import numpy as np
from PIL import Image, PngImagePlugin

from biovault.validation import validate_share_png
from .contracts import InvalidImageFormatError
from .encoder import validate_bits


def bits_to_png_bytes(bits: np.ndarray, *, pair_id: str | None = None) -> bytes:
    validate_bits(bits)
    out = BytesIO()
    pnginfo = PngImagePlugin.PngInfo()
    if pair_id is not None:
        pnginfo.add_text("biovault_pair_id", pair_id)
    Image.fromarray((1 - bits) * 255).save(out, format="PNG", pnginfo=pnginfo)
    return out.getvalue()


def png_bytes_to_bits(png_bytes: bytes) -> np.ndarray:
    validate_share_png(png_bytes)
    with Image.open(BytesIO(png_bytes)) as image:
        pixels = np.asarray(image.convert("L"), dtype=np.uint8)
    if np.any((pixels != 0) & (pixels != 255)):
        raise InvalidImageFormatError("PNG pixels must be exactly black or white.")
    return (pixels == 0).astype(np.uint8)
