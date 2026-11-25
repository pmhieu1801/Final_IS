"""M3 SQLite storage adapted for S2 and authenticated pair metadata."""

from contextlib import closing
from dataclasses import asdict
import json
import os
from pathlib import Path
import secrets
import sqlite3
from tempfile import NamedTemporaryFile

from .contracts import VaultRecord
from .security import generate_hmac, verify_hmac
from .validation import UserInputError

DATABASE_NAME = "vault.sqlite3"
KEY_NAME = "vault.key"
KEY_SIZE = 32


class RecordNotFound(UserInputError):
    pass


class MissingShare(UserInputError):
    pass


class IntegrityFailure(UserInputError):
    pass


class VaultConfigurationError(RuntimeError):
    pass


def open_local_vault(directory: Path) -> "SQLiteVault":
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    database = directory / DATABASE_NAME
    key_path = directory / KEY_NAME
    if not key_path.exists() and not database.exists():
        # Publish a complete key atomically. Concurrent starters reuse the winner.
        pending = NamedTemporaryFile(dir=directory, delete=False)
        try:
            with pending:
                pending.write(secrets.token_bytes(KEY_SIZE))
            os.link(pending.name, key_path)
        except FileExistsError:
            pass
        finally:
            Path(pending.name).unlink()
    try:
        with key_path.open("rb") as key_file:
            key = key_file.read(KEY_SIZE + 1)
    except FileNotFoundError as exc:
        raise VaultConfigurationError("The vault key is missing. Restore the key that belongs to this database.") from exc
    return SQLiteVault(database, key)


class SQLiteVault:
    def __init__(self, database: Path, key: bytes):
        if len(key) != KEY_SIZE:
            raise VaultConfigurationError("The vault needs a valid 32-byte key.")
        self.database = database
        self._key = key
        with closing(self._connect()) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS records (
                    record_id TEXT PRIMARY KEY NOT NULL,
                    pair_id TEXT UNIQUE NOT NULL,
                    metadata BLOB NOT NULL,
                    metadata_tag BLOB NOT NULL,
                    s1_tag BLOB NOT NULL
                );
                CREATE TABLE IF NOT EXISTS server_shares (
                    pair_id TEXT PRIMARY KEY NOT NULL REFERENCES records(pair_id) ON DELETE CASCADE,
                    png BLOB NOT NULL,
                    s2_tag BLOB NOT NULL
                );
            """)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @staticmethod
    def _message(role: bytes, metadata: bytes, share: bytes = b"") -> bytes:
        return b"BioVault/v1\0" + role + b"\0" + len(metadata).to_bytes(4, "big") + metadata + share

    def _record(self, row: sqlite3.Row) -> VaultRecord:
        metadata = row["metadata"]
        if not isinstance(metadata, bytes) or not verify_hmac(
            self._message(b"metadata", metadata), row["metadata_tag"], self._key
        ):
            raise IntegrityFailure("Record metadata failed its integrity check.")
        record = VaultRecord(**json.loads(metadata))
        if (record.record_id, record.pair_id) != (row["record_id"], row["pair_id"]):
            raise IntegrityFailure("The authenticated record identifiers do not match the vault index.")
        return record

    def save(self, record: VaultRecord, share2_png: bytes, share1_png: bytes) -> None:
        metadata = json.dumps(asdict(record), sort_keys=True, separators=(",", ":")).encode("utf-8")
        metadata_tag = generate_hmac(self._message(b"metadata", metadata), self._key)
        s1_tag = generate_hmac(self._message(b"S1", metadata, share1_png), self._key)
        s2_tag = generate_hmac(self._message(b"S2", metadata, share2_png), self._key)
        try:
            with closing(self._connect()) as conn, conn:
                conn.execute(
                    "INSERT INTO records VALUES (?, ?, ?, ?, ?)",
                    (record.record_id, record.pair_id, metadata, metadata_tag, s1_tag),
                )
                conn.execute(
                    "INSERT INTO server_shares VALUES (?, ?, ?)", (record.pair_id, share2_png, s2_tag)
                )
        except sqlite3.IntegrityError as exc:
            if exc.sqlite_errorcode in (sqlite3.SQLITE_CONSTRAINT_PRIMARYKEY, sqlite3.SQLITE_CONSTRAINT_UNIQUE):
                raise UserInputError("A vault record with these IDs already exists.") from exc
            raise

    def list_records(self) -> list[VaultRecord]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT record_id, pair_id, metadata, metadata_tag FROM records ORDER BY rowid DESC"
            )
            return [self._record(row) for row in rows]

    def verified_pair(self, pair_id: str, share1_png: bytes) -> tuple[VaultRecord, bytes]:
        with closing(self._connect()) as conn:
            row = conn.execute("""
                SELECT records.*, server_shares.png, server_shares.s2_tag
                FROM records LEFT JOIN server_shares USING (pair_id)
                WHERE records.pair_id = ?
            """, (pair_id,)).fetchone()

        if row is None:
            raise RecordNotFound("The selected record could not be found.")
        record = self._record(row)
        metadata = row["metadata"]
        if not verify_hmac(self._message(b"S1", metadata, share1_png), row["s1_tag"], self._key):
            raise IntegrityFailure("S1 failed the pair integrity check. Upload the original PNG for this record.")
        share2_png = row["png"]
        if share2_png is None:
            raise MissingShare("S2 is missing from the vault for this record.")
        if not isinstance(share2_png, bytes) or not verify_hmac(
            self._message(b"S2", metadata, share2_png), row["s2_tag"], self._key
        ):
            raise IntegrityFailure("S2 failed its vault integrity check.")
        return record, share2_png
