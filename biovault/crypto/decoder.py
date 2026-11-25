"""M2's digital XOR and equal-subpixel collapse rule."""

import numpy as np

from .contracts import InvalidImageFormatError, InvalidSubpixelBlockError, VerifiedPair
from .encoder import validate_bits


def reconstruct(verified_pair: VerifiedPair) -> np.ndarray:
    s1, s2 = verified_pair.s1_bits, verified_pair.s2_bits
    validate_bits(s1)
    validate_bits(s2)
    height, width = s1.shape
    if s1.shape != s2.shape or width % 2 or (height, width // 2) != verified_pair.p_shape:
        raise InvalidImageFormatError("Share dimensions do not match the declared secret dimensions.")

    xor_result = np.bitwise_xor(s1, s2)
    left, right = xor_result[:, ::2], xor_result[:, 1::2]
    if np.any(left != right):
        raise InvalidSubpixelBlockError("XOR contains a mixed subpixel block.")
    if np.any(s1[:, ::2] == s1[:, 1::2]) or np.any(s2[:, ::2] == s2[:, 1::2]):
        raise InvalidSubpixelBlockError("Each input share block must contain one black and one white subpixel.")
    return left.copy()
