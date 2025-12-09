from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from rundeck_mcp.models.base import MAX_RESULTS


class JobOption(BaseModel):
    """A job option definition.

    Job options define the parameters that can be passed when running a job.
    Options may be required, have default values, or be restricted to a list
    of allowed values.
    """

    name: str = Field(description="The option name/identifier")
    description: str | None = Field(default=None, description="Description of what this option does")
    required: bool = Field(default=False, description="Whether this option must be provided")
    value: str | None = Field(default=None, description="Default value for this option")
    values: list[str] | None = Field(
        default=None,
        description="List of allowed values. If set, the option value must be one of these.",
    )
    enforced: bool = Field(
        default=False,
        description="If true and values is set, the value must be from the allowed list",
    )
    multivalued: bool = Field(default=False, description="Whether multiple values can be selected")
    delimiter: str | None = Field(default=None, description="Delimiter for multivalued options")
    secure: bool = Field(default=False, description="Whether this is a secure/password option")
    storage_path: str | None = Field(default=None, description="Key storage path for secure options")
    option_type: str | None = Field(default=None, alias="type", description="Option type (e.g., 'file')")

    @computed_field
    @property
    def option_summary(self) -> str:
        """Generate a human-readable summary of this option."""
        parts = [f"'{self.name}'"]

        if self.required:
            parts.append("[REQUIRED]")

        if self.value:
            parts.append(f"(default: '{self.value}')")

        if self.values:
            allowed = ", ".join(self.values[:5])
            if len(self.values) > 5:
                allowed += f", ... ({len(self.values)} total)"
            parts.append(f"[allowed: {allowed}]")

        if self.description:
            parts.append(f"- {self.description}")

        return " ".join(parts)


class JobReference(BaseModel):
    """A minimal reference to a job, used in execution responses."""

    id: str = Field(description="The job UUID")
    name: str = Field(description="The job name")
    group: str | None = Field(default=None, description="The job group path")
    project: str = Field(description="The project name")
    href: str | None = Field(default=None, description="API URL for this job")
    permalink: str | None = Field(default=None, description="Web UI URL for this job")


class Job(BaseModel):
    """A Rundeck job definition.

    Jobs are the core automation unit in Rundeck. They define a sequence of steps
    to execute, along with options that parameterize the execution.
    """

    id: str = Field(description="The job UUID")
    name: str = Field(description="The job name")
    group: str | None = Field(default=None, description="The job group path (e.g., 'deploy/production')")
    project: str = Field(description="The project this job belongs to")
    description: str | None = Field(default=None, description="Job description")
    href: str | None = Field(default=None, description="API URL for this job")
    permalink: str | None = Field(default=None, description="Web UI URL for this job")
    scheduled: bool = Field(default=False, description="Whether this job has a schedule")
    schedule_enabled: bool = Field(default=True, description="Whether the schedule is enabled")
    enabled: bool = Field(default=True, description="Whether the job is enabled for execution")
    average_duration: int | None = Field(
        default=None,
        alias="averageDuration",
        description="Average execution duration in milliseconds",
    )
    options: list[JobOption] | None = Field(
        default=None,
        description="List of options/parameters for this job",
    )

    @computed_field
    @property
    def options_summary(self) -> str | None:
        """Generate a summary of job options for display."""
        if not self.options:
            return None

        lines = ["Job Options:"]
        for opt in self.options:
            lines.append(f"  - {opt.option_summary}")
        return "\n".join(lines)

    @computed_field
    @property
    def required_options(self) -> list[str]:
        """List of required option names that must be provided."""
        if not self.options:
            return []
        return [opt.name for opt in self.options if opt.required]

    @computed_field
    @property
    def type(self) -> Literal["job"]:
        return "job"


class JobQuery(BaseModel):
    """Query parameters for listing jobs."""

    model_config = ConfigDict(extra="forbid")

    project: str = Field(description="Project name (required)")
    group_path: str | None = Field(
        default=None,
        description="Filter by group path. Use '*' for all groups, '' for root level only.",
    )
    job_filter: str | None = Field(
        default=None,
        description="Filter by job name (substring match)",
    )
    job_exact_filter: str | None = Field(
        default=None,
        description="Filter by exact job name",
    )
    group_path_exact: str | None = Field(
        default=None,
        description="Filter by exact group path",
    )
    scheduled_filter: bool | None = Field(
        default=None,
        description="Filter to only scheduled jobs (true) or only non-scheduled (false)",
    )
    tags: str | None = Field(
        default=None,
        description="Filter by tags (comma-separated)",
    )
    limit: int = Field(
        default=MAX_RESULTS,
        ge=1,
        le=MAX_RESULTS,
        description="Maximum number of results to return",
    )

    def to_params(self) -> dict[str, Any]:
        """Convert query to API parameters."""
        params: dict[str, Any] = {}
        if self.group_path is not None:
            params["groupPath"] = self.group_path
        if self.job_filter:
            params["jobFilter"] = self.job_filter
        if self.job_exact_filter:
            params["jobExactFilter"] = self.job_exact_filter
        if self.group_path_exact:
            params["groupPathExact"] = self.group_path_exact
        if self.scheduled_filter is not None:
            params["scheduledFilter"] = self.scheduled_filter
        if self.tags:
            params["tags"] = self.tags
        if self.limit:
            params["max"] = self.limit
        return params


class JobRunRequest(BaseModel):
    """Request model for running a job.

    Options can be provided as a dictionary mapping option names to values.
    For options with allowed values lists, the value must be from that list.
    Required options must be provided.
    """

    model_config = ConfigDict(extra="forbid")

    options: dict[str, str] | None = Field(
        default=None,
        description="Job options as key-value pairs (e.g., {'version': '1.2.3', 'env': 'prod'})",
    )
    log_level: Literal["DEBUG", "VERBOSE", "INFO", "WARN", "ERROR"] | None = Field(
        default=None,
        description="Log level for the execution",
    )
    as_user: str | None = Field(
        default=None,
        description="Run the job as this user (requires 'runAs' permission)",
    )
    node_filter: str | None = Field(
        default=None,
        description="Override the node filter for this execution",
    )

    def to_request_body(self) -> dict[str, Any]:
        """Convert to API request body."""
        body: dict[str, Any] = {}
        if self.options:
            body["options"] = self.options
        if self.log_level:
            body["loglevel"] = self.log_level
        if self.as_user:
            body["asUser"] = self.as_user
        if self.node_filter:
            body["filter"] = self.node_filter
        return body


class JobRunResponse(BaseModel):
    """Response from running a job."""

    id: int = Field(description="The execution ID")
    href: str = Field(description="API URL for this execution")
    permalink: str = Field(description="Web UI URL for this execution")
    status: str = Field(description="Initial execution status (typically 'running')")
    project: str = Field(description="The project name")
    job: JobReference = Field(description="Reference to the job that was executed")
    description: str | None = Field(default=None, description="Execution description")
    argstring: str | None = Field(default=None, description="The argument string used")
    user: str = Field(description="The user who started the execution")
    date_started: dict[str, Any] | None = Field(
        default=None,
        alias="date-started",
        description="Start time information",
    )
