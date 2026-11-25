"""M2 basis matrices and secure column permutation."""

import secrets

import numpy as np

B0 = np.array([[1, 0], [1, 0]], dtype=np.uint8)
B1 = np.array([[1, 0], [0, 1]], dtype=np.uint8)


def get_random_permutation_columns(basis_matrix: np.ndarray) -> np.ndarray:
    col_perm = basis_matrix.copy()
    if secrets.randbelow(2) == 1:
        col_perm = col_perm[:, [1, 0]]
    return col_perm
