from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


def _as_utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes; they are always stored in UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, description="Folder name")
    allowed_roles: Optional[list[str]] = Field(
        default=None,
        description="Role names allowed to access the folder (default: all roles)",
    )

    @field_validator("name")
    @classmethod
    def _strip_and_reject_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Folder name cannot be blank")
        return cleaned


class FolderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Folder identifier")
    name: str = Field(description="Folder name")
    document_count: int = Field(description="Number of active documents in the folder")
    allowed_roles: list[str] = Field(description="Role names with access to the folder")
    created_at: datetime = Field(description="Creation timestamp (UTC)")

    @field_serializer("created_at")
    def _serialize_created_at(self, value: datetime) -> datetime:
        return _as_utc(value)


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Document identifier")
    original_filename: str = Field(description="Filename as provided by the client")
    file_extension: str = Field(description="Normalised file extension, without dot")
    mime_type: str = Field(description="Declared MIME type")
    file_size: int = Field(description="File size in bytes")
    folder_id: Optional[str] = Field(default=None, description="Owning folder id")
    folder_name: Optional[str] = Field(default=None, description="Owning folder name")
    status: str = Field(
        description=(
            "Indexing status: uploaded, processing, indexed, failed "
            "or pending_retry"
        )
    )
    chunk_count: int = Field(description="Number of indexed chunks")
    index_error: Optional[str] = Field(
        default=None, description="Last indexing error, if the status is 'failed'"
    )
    created_at: datetime = Field(description="Upload timestamp (UTC)")
    updated_at: datetime = Field(description="Last update timestamp (UTC)")

    @field_serializer("created_at", "updated_at")
    def _serialize_datetime(self, value: datetime) -> datetime:
        return _as_utc(value)


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse] = Field(description="Matching documents")
    total: int = Field(description="Total number of matching documents")


class DocumentDeleteResponse(BaseModel):
    id: str = Field(description="Deleted document identifier")
    status: str = Field(description="Always 'deleted'")


class IndexDocumentResponse(BaseModel):
    document_id: str = Field(description="Indexed document identifier")
    status: str = Field(
        description=(
            "Resulting status: indexed, failed or pending_retry "
            "(HTTP 429 quota, will be retried); processing when another "
            "index run already owns the document and continues in the "
            "background"
        )
    )
    progress: int = Field(ge=0, le=100, description="Progress percentage reached")
    chunk_count: int = Field(description="Number of chunks written")
    error: Optional[str] = Field(
        default=None,
        description="Failure detail when status is 'failed' (never pending_retry)",
    )
    peak_rss_mb: Optional[int] = Field(
        default=None, description="Peak process RSS during indexing (MB)"
    )


class DocumentPermissionCreate(BaseModel):
    document_id: str = Field(description="Document to grant access to")
    role: str = Field(min_length=1, max_length=50, description="Role name to grant")


class DocumentPermissionResponse(BaseModel):
    id: str = Field(description="Permission identifier")
    document_id: str = Field(description="Document identifier")
    role: str = Field(description="Role name with access")
    created_at: datetime = Field(description="Grant timestamp (UTC)")

    @field_serializer("created_at")
    def _serialize_created_at(self, value: datetime) -> datetime:
        return _as_utc(value)
