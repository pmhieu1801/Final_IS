"""Measured evaluations and isolated synthetic vault scenarios."""

from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from time import perf_counter

import numpy as np

from .crypto.adapter import BasisCrypto
from .crypto.basis import B0, B1
from .crypto.share_codec import bits_to_png_bytes, png_bytes_to_bits
from .orchestrator import AppWorkflow
from .storage import IntegrityFailure, MissingShare, open_local_vault

SAMPLE_PATH = Path(__file__).resolve().parents[1] / "samples" / "synthetic_biometric_pattern.png"
SCENARIOS = (
    "Only S1 is exposed",
    "Only S2 is exposed",
    "Both matching shares are exposed",
    "Incorrect share pairing",
    "S1 pixels are modified",
    "S2 is missing",
    "S2 is corrupted",
)


@dataclass(frozen=True)
class Evaluation:
    generation_ms: float
    reconstruction_ms: float
    processed_dimensions: tuple[int, int]
    share_dimensions: tuple[int, int]
    s1_bytes: int
    s2_bytes: int
    pixel_errors: int
    accuracy: float


@dataclass(frozen=True)
class ScenarioResult:
    observed: str
    implication: str
    image: bytes | None = None
    image_caption: str = ""


def evaluate(max_dimension: int) -> Evaluation:
    with TemporaryDirectory(prefix="biovault-evaluation-") as directory:
        workflow = AppWorkflow(BasisCrypto(), open_local_vault(Path(directory)))
        binary = workflow.prepare(SAMPLE_PATH.read_bytes(), SAMPLE_PATH.name, 128, max_dimension)
        start = perf_counter()
        result = workflow.generate(binary, SAMPLE_PATH.name)
        generation_ms = (perf_counter() - start) * 1000
        shares = result.shares
        workflow.save(result)
        start = perf_counter()
        recovered = workflow.recover(result.record.pair_id, shares.share1_png)
        reconstruction_ms = (perf_counter() - start) * 1000
    expected = png_bytes_to_bits(binary.png)
    errors = int(np.count_nonzero(expected != png_bytes_to_bits(recovered.image_png)))
    return Evaluation(
        generation_ms, reconstruction_ms, (binary.width, binary.height),
        (shares.share_width, shares.share_height), len(shares.share1_png), len(shares.share2_png),
        errors, 100 * (1 - errors / expected.size),
    )


def _patterns(row: int, basis: np.ndarray) -> list[str]:
    block = "".join(str(bit) for bit in basis[row])
    return sorted((block, block[::-1]))


def run_scenario(scenario: str) -> ScenarioResult:
    if scenario not in SCENARIOS:
        raise ValueError("Unknown Security Lab scenario.")
    with TemporaryDirectory(prefix="biovault-lab-") as directory:
        vault = open_local_vault(Path(directory))
        workflow = AppWorkflow(BasisCrypto(), vault)
        source = SAMPLE_PATH.read_bytes()
        sample = workflow.protect(source, SAMPLE_PATH.name, max_dimension=128)
        record, shares = sample.record, sample.shares
        if scenario in SCENARIOS[:2]:
            row = SCENARIOS.index(scenario)
            white, black = _patterns(row, B0), _patterns(row, B1)
            image = shares.share1_png if row == 0 else shares.share2_png
            return ScenarioResult(
                f"White pixel produces {' or '.join(white)}. Black pixel produces {' or '.join(black)}. "
                "The two column orders are equiprobable.",
                "A single share has the same distribution for every secret of the same dimensions, "
                "given fresh independent permutations.",
                image,
                f"Generated synthetic S{row + 1}",
            )
        if scenario == SCENARIOS[2]:
            image = workflow.crypto.reconstruct(shares.share1_png, shares.share2_png, record)
            errors = int(np.count_nonzero(png_bytes_to_bits(image) != png_bytes_to_bits(sample.binary_image.png)))
            return ScenarioResult(
                f"XOR recovered the binary image with {errors} pixel errors without a vault key.",
                "Possession of both corresponding shares is sufficient to reconstruct the processed image.",
                image,
                "Reconstructed synthetic image",
            )

        s1 = shares.share1_png
        if scenario == SCENARIOS[3]:
            s1 = workflow.protect(source, "different_pair.png", max_dimension=128).shares.share1_png
            implication = "A same-size share from a different pair is rejected by the authenticated S1 binding."
        elif scenario == SCENARIOS[4]:
            bits = png_bytes_to_bits(s1)
            bits[0, :2] ^= 1
            s1 = bits_to_png_bytes(bits, pair_id=record.pair_id)
            implication = "Flipping both subpixels preserves the block shape. The HMAC detects the change before XOR."
        elif scenario == SCENARIOS[5]:
            with closing(sqlite3.connect(vault.database)) as conn, conn:
                conn.execute("DELETE FROM server_shares WHERE pair_id = ?", (record.pair_id,))
            implication = "Recovery requires both shares. The record still exists, but its S2 is unavailable."
        else:
            with closing(sqlite3.connect(vault.database)) as conn, conn:
                conn.execute("UPDATE server_shares SET png = ? WHERE pair_id = ?", (b"corrupt", record.pair_id))
            implication = "The stored S2 fails authentication before the decoder receives it."

        try:
            workflow.recover(record.pair_id, s1)
        except (IntegrityFailure, MissingShare) as exc:
            return ScenarioResult(f"Reconstruction blocked. {exc}", implication)
        return ScenarioResult("Unexpected result. Reconstruction was accepted.", "The expected rejection did not occur.")
