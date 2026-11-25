"""PNG-oriented application contracts adapted from M1."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class BinaryImage:
    png: bytes
    width: int
    height: int
    threshold: int


@dataclass(frozen=True)
class SharePair:
    share1_png: bytes
    share2_png: bytes
    scheme_id: str
    secret_width: int
    secret_height: int
    share_width: int
    share_height: int
    expansion: int


@dataclass(frozen=True)
class VaultRecord:
    record_id: str
    pair_id: str
    display_name: str
    scheme_id: str
    created_at: str
    secret_width: int
    secret_height: int
    share_width: int
    share_height: int
    expansion: int
    threshold: int


@dataclass(frozen=True)
class ProtectResult:
    record: VaultRecord
    binary_image: BinaryImage
    shares: SharePair


@dataclass(frozen=True)
class RecoverResult:
    record: VaultRecord
    image_png: bytes


class CryptoPort(Protocol):
    def preprocess(self, raw_image: bytes, threshold: int, max_dimension: int) -> BinaryImage: ...
    def encode(self, binary_image: BinaryImage, pair_id: str) -> SharePair: ...
    def reconstruct(self, share1_png: bytes, share2_png: bytes, record: VaultRecord) -> bytes: ...


class VaultPort(Protocol):
    def save(self, record: VaultRecord, share2_png: bytes, share1_png: bytes) -> None: ...
    def list_records(self) -> list[VaultRecord]: ...
    def verified_pair(self, pair_id: str, share1_png: bytes) -> tuple[VaultRecord, bytes]: ...
