from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from rundeck_mcp.models.base import MAX_RESULTS
from rundeck_mcp.models.jobs import JobReference

ExecutionStatus = Literal["running", "succeeded", "failed", "aborted", "timedout", "scheduled"]


class LogEntry(BaseModel):
    """A single log entry from an execution."""

    time: str | None = Field(default=None, description="Timestamp of the log entry")
    absolute_time: str | None = Field(
        default=None,
        alias="absolute_time",
        description="Absolute timestamp",
    )
    level: str = Field(default="NORMAL", description="Log level (e.g., NORMAL, ERROR, WARN, DEBUG)")
    log: str = Field(description="The log message content")
    node: str | None = Field(default=None, description="Node that produced this log entry")
    step: str | None = Field(default=None, alias="stepctx", description="Step context identifier")
    user: str | None = Field(default=None, description="User associated with this log entry")


class ExecutionOutput(BaseModel):
    """Output/logs from a job execution.

    Contains the log entries and metadata about the output retrieval.
    Use the 'completed' field to determine if the execution has finished.
    """

    id: int = Field(description="The execution ID")
    offset: int = Field(default=0, description="Byte offset in the log file")
    completed: bool = Field(description="Whether the execution has completed")
    exec_completed: bool = Field(
        default=False,
        alias="execCompleted",
        description="Whether execution is complete",
    )
    has_more_output: bool = Field(
        default=False,
        alias="hasMoreOutput",
        description="Whether more output is available",
    )
    exec_state: str | None = Field(
        default=None,
        alias="execState",
        description="Current execution state",
    )
    exec_duration: int | None = Field(
        default=None,
        alias="execDuration",
        description="Execution duration in milliseconds",
    )
    percent_loaded: float | None = Field(
        default=None,
        alias="percentLoaded",
        description="Percentage of output loaded (0-100)",
    )
    total_size: int | None = Field(
        default=None,
        alias="totalSize",
        description="Total size of log file in bytes",
    )
    entries: list[LogEntry] = Field(default_factory=list, description="Log entries")

    @computed_field
    @property
    def output_summary(self) -> str:
        """Generate a summary of the output."""
        status = "COMPLETE" if self.completed else "IN PROGRESS"
        lines = [f"Execution Output (ID: {self.id}) - {status}"]

        if self.exec_duration:
            seconds = self.exec_duration / 1000
            lines.append(f"Duration: {seconds:.1f}s")

        if self.percent_loaded is not None:
            lines.append(f"Loaded: {self.percent_loaded:.1f}%")

        lines.append(f"Log entries: {len(self.entries)}")

        if self.has_more_output:
            lines.append("NOTE: More output available (use offset parameter)")

        return "\n".join(lines)


class Execution(BaseModel):
    """A job execution instance.

    Represents a single run of a job, including its status, timing, and results.
    """

    id: int = Field(description="The execution ID")
    href: str | None = Field(default=None, description="API URL for this execution")
    permalink: str | None = Field(default=None, description="Web UI URL for this execution")
    status: ExecutionStatus = Field(description="Execution status")
    project: str = Field(description="The project name")
    job: JobReference | None = Field(default=None, description="Reference to the job (None for adhoc executions)")
    user: str = Field(description="User who started this execution")
    date_started: datetime | None = Field(
        default=None,
        alias="date-started",
        description="When the execution started",
    )
    date_ended: datetime | None = Field(
        default=None,
        alias="date-ended",
        description="When the execution ended (None if still running)",
    )
    argstring: str | None = Field(
        default=None,
        description="The argument string used for this execution",
    )
    description: str | None = Field(default=None, description="Execution description")
    successful_nodes: list[str] | None = Field(
        default=None,
        alias="successfulNodes",
        description="List of nodes that succeeded",
    )
    failed_nodes: list[str] | None = Field(
        default=None,
        alias="failedNodes",
        description="List of nodes that failed",
    )

    @field_validator("date_started", "date_ended", mode="before")
    @classmethod
    def parse_date_dict(cls, v: Any) -> datetime | None:
        """Parse date from Rundeck's dict format or ISO string."""
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, dict):
            # Rundeck returns {"unixtime": 1234567890, "date": "..."}
            if "unixtime" in v:
                return datetime.fromtimestamp(v["unixtime"] / 1000)
            if "date" in v:
                return datetime.fromisoformat(v["date"].replace("Z", "+00:00"))
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return None

    @computed_field
    @property
    def duration_seconds(self) -> float | None:
        """Calculate duration in seconds."""
        if self.date_started and self.date_ended:
            return (self.date_ended - self.date_started).total_seconds()
        return None

    @computed_field
    @property
    def execution_summary(self) -> str:
        """Generate a human-readable summary of this execution."""
        parts = [f"Execution #{self.id}: {self.status.upper()}"]

        if self.job:
            parts.append(f"Job: {self.job.name}")
            if self.job.group:
                parts[-1] = f"Job: {self.job.group}/{self.job.name}"

        if self.user:
            parts.append(f"User: {self.user}")

        if self.duration_seconds is not None:
            parts.append(f"Duration: {self.duration_seconds:.1f}s")

        if self.argstring:
            parts.append(f"Args: {self.argstring}")

        return " | ".join(parts)

    @computed_field
    @property
    def type(self) -> Literal["execution"]:
        return "execution"


class ExecutionQuery(BaseModel):
    """Query parameters for listing executions."""

    model_config = ConfigDict(extra="forbid")

    project: str | None = Field(
        default=None,
        description="Filter by project name",
    )
    job_id: str | None = Field(
        default=None,
        description="Filter by job ID (UUID)",
    )
    status: ExecutionStatus | None = Field(
        default=None,
        description="Filter by execution status",
    )
    user: str | None = Field(
        default=None,
        description="Filter by user who started the execution",
    )
    recent_filter: str | None = Field(
        default=None,
        description="Filter by recent time period (e.g., '1h', '1d', '1w')",
    )
    older_filter: str | None = Field(
        default=None,
        description="Filter for executions older than this period",
    )
    begin: datetime | None = Field(
        default=None,
        description="Filter for executions started after this time",
    )
    end: datetime | None = Field(
        default=None,
        description="Filter for executions started before this time",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=MAX_RESULTS,
        description="Maximum number of results to return",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Offset for pagination",
    )

    def to_params(self) -> dict[str, Any]:
        """Convert query to API parameters."""
        params: dict[str, Any] = {"max": self.limit, "offset": self.offset}

        if self.status:
            params["statusFilter"] = self.status
        if self.user:
            params["userFilter"] = self.user
        if self.recent_filter:
            params["recentFilter"] = self.recent_filter
        if self.older_filter:
            params["olderFilter"] = self.older_filter
        if self.begin:
            params["begin"] = int(self.begin.timestamp() * 1000)
        if self.end:
            params["end"] = int(self.end.timestamp() * 1000)

        return params
