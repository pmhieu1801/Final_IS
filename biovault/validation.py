"""Upload limits and format checks adapted from M1."""

from io import BytesIO
from pathlib import PureWindowsPath

from PIL import Image, ImageOps

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 3_000_000
MAX_PROCESSED_DIMENSION = 1024
SUPPORTED = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG"}
IMAGE_ERRORS = (OSError, ValueError, Image.DecompressionBombError, SyntaxError, OverflowError)


class UserInputError(ValueError):
    pass


def _check_size(raw: bytes) -> None:
    if not raw or len(raw) > MAX_UPLOAD_BYTES:
        raise UserInputError("Choose a nonempty file no larger than 8 MB.")


def validate_image(raw: bytes, filename: str) -> tuple[int, int]:
    _check_size(raw)
    expected_format = SUPPORTED.get(PureWindowsPath(filename).suffix.lower())
    if expected_format is None:
        raise UserInputError("Upload a PNG or JPEG image.")
    try:
        with Image.open(BytesIO(raw)) as image:
            if image.format != expected_format:
                raise UserInputError("The image content must match its PNG or JPEG extension.")
            if getattr(image, "n_frames", 1) != 1:
                raise UserInputError("Upload a single-frame image.")
            width, height = image.size
            if min(width, height) < 16 or width * height > MAX_PIXELS:
                raise UserInputError("Images must be at least 16 × 16 pixels and at most 3 million pixels.")
            image.verify()
        with Image.open(BytesIO(raw)) as image:
            return ImageOps.exif_transpose(image).size
    except UserInputError:
        raise
    except IMAGE_ERRORS as exc:
        raise UserInputError("The image is invalid or corrupted.") from exc


def validate_share_png(raw: bytes) -> tuple[int, int]:
    _check_size(raw)
    try:
        with Image.open(BytesIO(raw)) as image:
            if image.format != "PNG" or image.mode not in ("1", "L") or image.n_frames != 1:
                raise UserInputError("Upload a single-frame grayscale share PNG.")
            width, height = image.size
            if width > 2 * MAX_PROCESSED_DIMENSION or height > MAX_PROCESSED_DIMENSION:
                raise UserInputError("The share dimensions exceed the supported limits.")
            image.verify()
        return width, height
    except UserInputError:
        raise
    except IMAGE_ERRORS as exc:
        raise UserInputError("The share PNG is invalid or corrupted.") from exc
