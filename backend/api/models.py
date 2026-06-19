"""
api/models.py — SQLAlchemy ORM models.

All tables defined here are auto-created at startup via init_db().
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, func #
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db import Base


class IngestionJob(Base):
    """Tracks the lifecycle of a repository ingestion job."""

    __tablename__ = "ingestion_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    status: Mapped[str] = mapped_column(
        Enum("pending", "cloning", "parsing", "embedding", "graphing", "ready", "failed", name="job_status"),
        default="pending",
        nullable=False,
        index=True,
    )
    # key    # this is mapped from db  # obj mai convert hote wakt it will be str             
    repo_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    repo_name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Ingestion metadata (populated as the pipeline runs)
    repo_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Error details if status == 'failed'
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Progress counters
    total_files: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processed_files: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    total_chunks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dict for API responses."""
        return {
            "job_id": str(self.id),
            "status": self.status,
            "repo_url": self.repo_url,
            "repo_name": self.repo_name,
            "metadata": self.repo_metadata,
            "error_message": self.error_message,
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "total_chunks": self.total_chunks,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
