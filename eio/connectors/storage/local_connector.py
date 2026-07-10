"""
Local File System Storage Connector
=====================================
Reads documents from a configurable local directory.
Used as the demo storage connector in the EIO MVP.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from eio.connectors.storage.base import DocumentMetadata, StorageConnector

_MIME_MAP = {
    "pdf": "application/pdf",
    "txt": "text/plain",
    "md": "text/markdown",
    "json": "application/json",
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class LocalFileSystemConnector(StorageConnector):
    """
    Storage connector backed by the local file system.
    The root directory is controlled by EIO_LOCAL_STORAGE_PATH.
    """

    def __init__(self, root_path: str) -> None:
        self._root = Path(root_path).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    # ── listing ────────────────────────────────────────────────────────────

    def list_documents(self, prefix: str = "") -> list[DocumentMetadata]:
        """Recursively list all files under root, optionally filtered by prefix."""
        results: list[DocumentMetadata] = []
        search_root = self._root / prefix if prefix else self._root

        if not search_root.exists():
            return results

        for file_path in sorted(search_root.rglob("*")):
            if not file_path.is_file():
                continue
            stat = file_path.stat()
            ext = file_path.suffix.lstrip(".").lower()
            results.append(
                DocumentMetadata(
                    name=file_path.name,
                    path=str(file_path.relative_to(self._root)),
                    size_bytes=stat.st_size,
                    content_type=_MIME_MAP.get(ext, "application/octet-stream"),
                    last_modified=datetime.fromtimestamp(stat.st_mtime),
                )
            )
        return results

    # ── read / write ────────────────────────────────────────────────────────

    def read_document(self, path: str) -> bytes:
        full_path = self._root / path
        if not full_path.exists():
            raise FileNotFoundError(f"Document not found: {path} (root: {self._root})")
        return full_path.read_bytes()

    def write_document(
        self, path: str, content: bytes, content_type: str = "application/octet-stream"
    ) -> DocumentMetadata:
        full_path = self._root / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)
        stat = full_path.stat()
        return DocumentMetadata(
            name=full_path.name,
            path=path,
            size_bytes=stat.st_size,
            content_type=content_type,
            last_modified=datetime.fromtimestamp(stat.st_mtime),
        )

    # ── health ─────────────────────────────────────────────────────────────

    def health_check(self) -> dict[str, Any]:
        try:
            exists = self._root.exists() and self._root.is_dir()
            readable = os.access(self._root, os.R_OK)
            if exists and readable:
                doc_count = sum(1 for _ in self._root.rglob("*") if _.is_file())
                return {
                    "status": "ok",
                    "connector": "local",
                    "root": str(self._root),
                    "document_count": doc_count,
                }
            return {
                "status": "error",
                "connector": "local",
                "detail": f"Root path not accessible: {self._root}",
            }
        except Exception as exc:
            return {"status": "error", "connector": "local", "detail": str(exc)}
