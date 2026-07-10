"""
Storage Connector Stubs
========================
Stub connectors for all supported document repositories.
Each raises NotImplementedError with installation instructions.
"""

from __future__ import annotations

from typing import Any

from eio.connectors.storage.base import DocumentMetadata, StorageConnector


def _not_implemented(connector: str, package: str, env_var: str) -> None:
    raise NotImplementedError(
        f"{connector} storage connector is not yet implemented.\n"
        f"  1. Install the SDK: pip install {package}\n"
        f"  2. Set {env_var} in your .env file\n"
        f"  3. Implement the connector in eio/connectors/storage/{connector.lower()}_connector.py\n"
        f"     by subclassing StorageConnector and registering with @StorageRegistry.register('{connector.lower()}')"
    )


class S3Connector(StorageConnector):
    """Amazon S3 connector stub. Implement using boto3."""
    def list_documents(self, prefix: str = "") -> list[DocumentMetadata]: _not_implemented("S3", "boto3", "EIO_S3_BUCKET")  # type: ignore
    def read_document(self, path: str) -> bytes: _not_implemented("S3", "boto3", "EIO_S3_BUCKET")  # type: ignore
    def write_document(self, path: str, content: bytes, content_type: str = "") -> DocumentMetadata: _not_implemented("S3", "boto3", "EIO_S3_BUCKET")  # type: ignore
    def health_check(self) -> dict[str, Any]: _not_implemented("S3", "boto3", "EIO_S3_BUCKET")  # type: ignore


class AzureBlobConnector(StorageConnector):
    """Azure Blob Storage connector stub. Implement using azure-storage-blob."""
    def list_documents(self, prefix: str = "") -> list[DocumentMetadata]: _not_implemented("AzureBlob", "azure-storage-blob", "EIO_AZURE_CONNECTION_STRING")  # type: ignore
    def read_document(self, path: str) -> bytes: _not_implemented("AzureBlob", "azure-storage-blob", "EIO_AZURE_CONNECTION_STRING")  # type: ignore
    def write_document(self, path: str, content: bytes, content_type: str = "") -> DocumentMetadata: _not_implemented("AzureBlob", "azure-storage-blob", "EIO_AZURE_CONNECTION_STRING")  # type: ignore
    def health_check(self) -> dict[str, Any]: _not_implemented("AzureBlob", "azure-storage-blob", "EIO_AZURE_CONNECTION_STRING")  # type: ignore


class GCSConnector(StorageConnector):
    """Google Cloud Storage connector stub. Implement using google-cloud-storage."""
    def list_documents(self, prefix: str = "") -> list[DocumentMetadata]: _not_implemented("GCS", "google-cloud-storage", "GOOGLE_APPLICATION_CREDENTIALS")  # type: ignore
    def read_document(self, path: str) -> bytes: _not_implemented("GCS", "google-cloud-storage", "GOOGLE_APPLICATION_CREDENTIALS")  # type: ignore
    def write_document(self, path: str, content: bytes, content_type: str = "") -> DocumentMetadata: _not_implemented("GCS", "google-cloud-storage", "GOOGLE_APPLICATION_CREDENTIALS")  # type: ignore
    def health_check(self) -> dict[str, Any]: _not_implemented("GCS", "google-cloud-storage", "GOOGLE_APPLICATION_CREDENTIALS")  # type: ignore


class IBMCOSConnector(StorageConnector):
    """IBM Cloud Object Storage connector stub. Implement using ibm-cos-sdk."""
    def list_documents(self, prefix: str = "") -> list[DocumentMetadata]: _not_implemented("IBMCOS", "ibm-cos-sdk", "EIO_IBMCOS_BUCKET")  # type: ignore
    def read_document(self, path: str) -> bytes: _not_implemented("IBMCOS", "ibm-cos-sdk", "EIO_IBMCOS_BUCKET")  # type: ignore
    def write_document(self, path: str, content: bytes, content_type: str = "") -> DocumentMetadata: _not_implemented("IBMCOS", "ibm-cos-sdk", "EIO_IBMCOS_BUCKET")  # type: ignore
    def health_check(self) -> dict[str, Any]: _not_implemented("IBMCOS", "ibm-cos-sdk", "EIO_IBMCOS_BUCKET")  # type: ignore


class SharePointConnector(StorageConnector):
    """SharePoint connector stub. Implement using Office365-REST-Python-Client."""
    def list_documents(self, prefix: str = "") -> list[DocumentMetadata]: _not_implemented("SharePoint", "Office365-REST-Python-Client", "EIO_SHAREPOINT_URL")  # type: ignore
    def read_document(self, path: str) -> bytes: _not_implemented("SharePoint", "Office365-REST-Python-Client", "EIO_SHAREPOINT_URL")  # type: ignore
    def write_document(self, path: str, content: bytes, content_type: str = "") -> DocumentMetadata: _not_implemented("SharePoint", "Office365-REST-Python-Client", "EIO_SHAREPOINT_URL")  # type: ignore
    def health_check(self) -> dict[str, Any]: _not_implemented("SharePoint", "Office365-REST-Python-Client", "EIO_SHAREPOINT_URL")  # type: ignore


class OneDriveConnector(StorageConnector):
    """OneDrive connector stub. Implement using msgraph-sdk."""
    def list_documents(self, prefix: str = "") -> list[DocumentMetadata]: _not_implemented("OneDrive", "msgraph-sdk", "EIO_ONEDRIVE_CLIENT_ID")  # type: ignore
    def read_document(self, path: str) -> bytes: _not_implemented("OneDrive", "msgraph-sdk", "EIO_ONEDRIVE_CLIENT_ID")  # type: ignore
    def write_document(self, path: str, content: bytes, content_type: str = "") -> DocumentMetadata: _not_implemented("OneDrive", "msgraph-sdk", "EIO_ONEDRIVE_CLIENT_ID")  # type: ignore
    def health_check(self) -> dict[str, Any]: _not_implemented("OneDrive", "msgraph-sdk", "EIO_ONEDRIVE_CLIENT_ID")  # type: ignore
