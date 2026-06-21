"""ModelRoutingStats ORM model (UCB bandit statistics per route + model)."""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.postgres import Base


class ModelRoutingStats(Base):
    __tablename__ = "model_routing_stats"
    __table_args__ = (
        UniqueConstraint("route_key", "model_name", name="uq_routing_route_model"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    workflow_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    node_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    route_key: Mapped[str] = mapped_column(String(512), nullable=False, index=True)

    pulls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_reward: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_reward: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
