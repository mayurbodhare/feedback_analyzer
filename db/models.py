from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Enum,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.sql import func
from .config import Base
import enum


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStage(str, enum.Enum):
    QUEUE = "queue"
    START_EMAIL = "start_email"
    TRANSLATION = "translation"
    INTENT = "intent"
    SENTIMENT = "sentiment"
    DISTRIBUTION_CHART = "distribution_chart"
    WORDCLOUD = "wordcloud"
    TREEMAP = "treemap"
    SUNBURST = "sunburst"
    SUMMARY = "summary"
    FINAL_EMAIL = "final_email"


class Task(Base):
    __tablename__ = "tasks"

    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(100), nullable=False, index=True)

    # Status tracking
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)
    stage = Column(Enum(TaskStage), default=TaskStage.QUEUE, nullable=False)

    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    # Results storage
    distribution_chart = Column(ARRAY(String), nullable=True)
    wordcloud = Column(ARRAY(String), nullable=True)
    treemap = Column(JSONB, nullable=True)
    sunburst = Column(JSONB, nullable=True)
    summary = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),         
        nullable=False
    )
    completed_at = Column(DateTime(timezone=True), nullable=True) 

    def __repr__(self):
        return f"<Task(id={self.id}, job_id='{self.job_id}', status='{self.status.value}')>"

    def __str__(self):
        return f"Task {self.job_id} - {self.status.value}"

    def mark_failed(self, error: str):
        """Mark task as failed with error message"""
        self.status = TaskStatus.FAILED
        self.error_message = error
        self.retry_count += 1

    def mark_completed(self):
        """Mark task as completed"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = func.now()

    def mark_in_progress(self):
        """Mark task as in progress"""
        self.status = TaskStatus.IN_PROGRESS

    