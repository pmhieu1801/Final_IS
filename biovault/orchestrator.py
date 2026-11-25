"""M1 application workflow connected to M2 cryptography and M3 storage."""

from datetime import datetime, timezone
from pathlib import PureWindowsPath
import secrets
from uuid import uuid4

from .contracts import BinaryImage, CryptoPort, ProtectResult, RecoverResult, VaultPort, VaultRecord
from .validation import MAX_PROCESSED_DIMENSION, UserInputError, validate_image, validate_share_png


class AppWorkflow:
    def __init__(self, crypto: CryptoPort, vault: VaultPort):
        self.crypto = crypto
        self.vault = vault

    def prepare(self, raw: bytes, filename: str, threshold: int = 128, max_dimension: int = 512) -> BinaryImage:
        validate_image(raw, filename)
        if not 1 <= threshold <= 254:
            raise UserInputError("Threshold must be between 1 and 254.")
        if not 32 <= max_dimension <= MAX_PROCESSED_DIMENSION:
            raise UserInputError("Maximum processed dimension must be between 32 and 1024.")
        return self.crypto.preprocess(raw, threshold, max_dimension)

    def generate(self, binary: BinaryImage, filename: str) -> ProtectResult:
        pair_id = secrets.token_hex(16)
        pair = self.crypto.encode(binary, pair_id)
        if (pair.secret_width, pair.secret_height) != (binary.width, binary.height):
            raise RuntimeError("The encoder returned inconsistent secret dimensions.")
        if (pair.share_width, pair.share_height) != (binary.width * pair.expansion, binary.height):
            raise RuntimeError("The encoder returned inconsistent share dimensions.")
        record = VaultRecord(
            record_id=uuid4().hex,
            pair_id=pair_id,
            display_name=PureWindowsPath(filename).name[:255],
            scheme_id=pair.scheme_id,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            secret_width=pair.secret_width,
            secret_height=pair.secret_height,
            share_width=pair.share_width,
            share_height=pair.share_height,
            expansion=pair.expansion,
            threshold=binary.threshold,
        )
        return ProtectResult(record, binary, pair)

    def save(self, result: ProtectResult) -> None:
        self.vault.save(result.record, result.shares.share2_png, result.shares.share1_png)

    def protect(self, raw: bytes, filename: str, threshold: int = 128, max_dimension: int = 512) -> ProtectResult:
        result = self.generate(self.prepare(raw, filename, threshold, max_dimension), filename)
        self.save(result)
        return result

    def recover(self, pair_id: str, client_share_png: bytes) -> RecoverResult:
        width, height = validate_share_png(client_share_png)
        record, server_share = self.vault.verified_pair(pair_id, client_share_png)
        if (width, height) != (record.share_width, record.share_height):
            raise UserInputError("The S1 dimensions do not match the selected record.")
        return RecoverResult(record, self.crypto.reconstruct(client_share_png, server_share, record))
