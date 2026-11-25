"""Connect M1's preprocessing and PNG workflow to M2's array engine."""

from io import BytesIO

import numpy as np
from PIL import Image, ImageOps

from biovault.contracts import BinaryImage, SharePair, VaultRecord
from biovault.validation import IMAGE_ERRORS, UserInputError
from .contracts import BioVaultAlgorithmError, SchemeSpec, VerifiedPair
from .decoder import reconstruct
from .encoder import generate
from .share_codec import bits_to_png_bytes, png_bytes_to_bits


class BasisCrypto:
    def preprocess(self, raw_image: bytes, threshold: int, max_dimension: int) -> BinaryImage:
        try:
            with Image.open(BytesIO(raw_image)) as source:
                gray = ImageOps.exif_transpose(source).convert("L")
                gray.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                bits = (np.asarray(gray) < threshold).astype(np.uint8)
        except IMAGE_ERRORS as exc:
            raise UserInputError("The image could not be decoded for preprocessing.") from exc
        return BinaryImage(bits_to_png_bytes(bits), gray.width, gray.height, threshold)

    def encode(self, binary_image: BinaryImage, pair_id: str) -> SharePair:
        pair = generate(png_bytes_to_bits(binary_image.png))
        height, width = pair.p_shape
        share_height, share_width = pair.share_shape
        return SharePair(
            bits_to_png_bytes(pair.s1_bits, pair_id=pair_id),
            bits_to_png_bytes(pair.s2_bits),
            pair.spec.identifier,
            width,
            height,
            share_width,
            share_height,
            pair.spec.expansion_m,
        )

    def reconstruct(self, share1_png: bytes, share2_png: bytes, record: VaultRecord) -> bytes:
        spec = SchemeSpec()
        if record.scheme_id != spec.identifier or record.expansion != spec.expansion_m:
            raise UserInputError("This record uses an unsupported cryptography scheme.")
        try:
            s1 = png_bytes_to_bits(share1_png)
            s2 = png_bytes_to_bits(share2_png)
            if s1.shape != (record.share_height, record.share_width):
                raise UserInputError("The share dimensions do not match the record.")
            bits = reconstruct(VerifiedPair(
                record.pair_id, s1, s2, (record.secret_height, record.secret_width)
            ))
        except (BioVaultAlgorithmError, OSError) as exc:
            raise UserInputError(f"Could not decode the share pair. {exc}") from exc
        return bits_to_png_bytes(bits)
