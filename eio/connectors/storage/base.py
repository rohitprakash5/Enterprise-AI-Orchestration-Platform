"""
Storage Connector Abstraction Layer
=====================================
All document repository drivers must implement the StorageConnector ABC.
Switching storage backends requires only an env-var change (EIO_ACTIVE_STORAGE).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Metadata for a stored document."""

    name: str
    path: str
    size_bytes: int = 0
    content_type: str = "application/octet-stream"
    last_modified: datetime | None = None

    @property
    def extension(self) -> str:
        return self.name.rsplit(".", 1)[-1].lower() if "." in self.name else ""


class StorageConnector(ABC):
    """
    Abstract base class for all EIO document storage connectors.

    Concrete implementations: LocalFileSystemConnector, S3Connector, etc.
    All connectors are registered in StorageRegistry and selected via
    the EIO_ACTIVE_STORAGE environment variable.
    """

    @abstractmethod
    def list_documents(self, prefix: str = "") -> list[DocumentMetadata]:
        """List all documents, optionally filtered by path prefix."""

    @abstractmethod
    def read_document(self, path: str) -> bytes:
        """Read a document and return its raw bytes."""

    @abstractmethod
    def write_document(self, path: str, content: bytes, content_type: str = "application/octet-stream") -> DocumentMetadata:
        """Write content to the given path and return its metadata."""

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Return health status: {"status": "ok"|"error", "detail": str}."""
