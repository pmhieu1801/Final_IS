"""Array contracts adapted from M2's app/contracts.py."""

from dataclasses import dataclass, field

import numpy as np


class BioVaultAlgorithmError(ValueError):
    pass


class InvalidImageFormatError(BioVaultAlgorithmError):
    pass


class InvalidSubpixelBlockError(BioVaultAlgorithmError):
    pass


@dataclass(frozen=True)
class SchemeSpec:
    scheme: str = "basis_matrix_xor"
    version: str = "1.0.0"
    expansion_m: int = 2

    @property
    def identifier(self) -> str:
        return f"{self.scheme}@{self.version}"


@dataclass
class SharePairData:
    s1_bits: np.ndarray
    s2_bits: np.ndarray
    p_shape: tuple[int, int]
    share_shape: tuple[int, int]
    spec: SchemeSpec = field(default_factory=SchemeSpec)


@dataclass
class VerifiedPair:
    pair_id: str
    s1_bits: np.ndarray
    s2_bits: np.ndarray
    p_shape: tuple[int, int]
