"""M2 encoding with horizontal pixel expansion m = 2."""

import numpy as np

from .basis import B0, B1, get_random_permutation_columns
from .contracts import InvalidImageFormatError, SharePairData


def validate_bits(bits: np.ndarray) -> None:
    if bits.ndim != 2 or not bits.size or bits.dtype != np.uint8 or np.any(bits > 1):
        raise InvalidImageFormatError("Expected a nonempty 2D uint8 array of binary values.")


def generate(P: np.ndarray) -> SharePairData:
    validate_bits(P)
    height, width = P.shape
    s1_bits = np.zeros((height, 2 * width), dtype=np.uint8)
    s2_bits = np.zeros_like(s1_bits)

    for y in range(height):
        for x in range(width):
            base = B0 if P[y, x] == 0 else B1
            permuted_basis = get_random_permutation_columns(base)
            s1_bits[y, 2 * x : 2 * x + 2] = permuted_basis[0, :]
            s2_bits[y, 2 * x : 2 * x + 2] = permuted_basis[1, :]

    return SharePairData(s1_bits, s2_bits, P.shape, s1_bits.shape)
