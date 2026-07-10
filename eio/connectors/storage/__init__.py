"""
Storage Connectors Package
============================
Auto-registers all connectors into the StorageRegistry on import.
"""

from eio.connectors.storage.local_connector import LocalFileSystemConnector
from eio.connectors.storage.registry import StorageRegistry

StorageRegistry.register("local")(LocalFileSystemConnector)

from eio.connectors.storage.stubs import (  # noqa: E402
    AzureBlobConnector,
    GCSConnector,
    IBMCOSConnector,
    OneDriveConnector,
    S3Connector,
    SharePointConnector,
)

StorageRegistry.register("s3")(S3Connector)
StorageRegistry.register("azure_blob")(AzureBlobConnector)
StorageRegistry.register("gcs")(GCSConnector)
StorageRegistry.register("ibm_cos")(IBMCOSConnector)
StorageRegistry.register("sharepoint")(SharePointConnector)
StorageRegistry.register("onedrive")(OneDriveConnector)

__all__ = ["StorageRegistry", "LocalFileSystemConnector"]
