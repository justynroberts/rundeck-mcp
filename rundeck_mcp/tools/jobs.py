from typing import Any

from rundeck_mcp.client import get_client
from rundeck_mcp.models import (
    Job,
    JobOption,
    JobQuery,
    JobReference,
    JobRunRequest,
    JobRunResponse,
)
from rundeck_mcp.utils import validate_job_options


def list_jobs(query: JobQuery) -> str:
    """List jobs in a Rundeck project with optional filtering.

    Returns a numbered markdown table of jobs. Use the # column to reference
    jobs in subsequent commands (e.g., "run job 3").

    Args:
        query: Query parameters for filtering jobs

    Returns:
        Markdown table with numbered jobs

    Examples:
        List all jobs in a project:
        >>> result = list_jobs(JobQuery(project="myproject"))

        Filter by group:
        >>> result = list_jobs(JobQuery(project="myproject", group_path="deploy/prod"))

        Search by name:
        >>> result = list_jobs(JobQuery(project="myproject", job_filter="backup"))
    """
    client = get_client()
    params = query.to_params()

    response = client.get(f"/project/{query.project}/jobs", params=params)

    if not response:
        return "No jobs found."

    jobs = []
    for job_data in response:
        jobs.append(_parse_job(job_data))

    return _format_jobs_table(jobs)


def get_job(job_id: str) -> str:
    """Get detailed information about a specific job.

    Returns the full job definition including all options displayed in a table
    showing required status, defaults, and allowed values.

    Args:
        job_id: The job UUID

    Returns:
        Formatted string with job details and options table

    Examples:
        >>> result = get_job("abc-123-def")
        >>> print(result)
        '## Deploy Application...'
    """
    client = get_client()
    response = client.get(f"/job/{job_id}")

    job = _parse_job(response)
    return _format_job_details(job)


def run_job(job_id: str, request: JobRunRequest | None = None) -> str:
    """Execute a Rundeck job with optional parameters.

    Before running, this tool validates that:
    - All required options are provided (or have defaults)
    - Option values match allowed values for enforced options

    If validation fails, returns a formatted error with an options table showing
    what's required and allowed values - ask the user for the missing values.

    Args:
        job_id: The job UUID to execute
        request: Optional execution parameters including options

    Returns:
        Formatted string with execution result or validation error with options table

    Examples:
        Run a job with no options:
        >>> result = run_job("abc-123-def")

        Run with options:
        >>> result = run_job(
        ...     "abc-123-def",
        ...     JobRunRequest(options={"version": "1.2.3", "env": "prod"})
        ... )
    """
    client = get_client()

    # Fetch job to validate options
    job_response = client.get(f"/job/{job_id}")
    job = _parse_job(job_response)
    job_options = job_response.get("options") if isinstance(job_response, dict) else None

    provided_options = request.options if request else None

    # Validate options
    is_valid, errors = validate_job_options(job_options, provided_options)

    if not is_valid:
        return _format_validation_error(job, errors, provided_options)

    # Build request body
    body = request.to_request_body() if request else {}

    # Execute job
    response = client.post(f"/job/{job_id}/run", json=body)

    return _format_run_response(_parse_run_response(response))


def _format_jobs_table(jobs: list[Job]) -> str:
    """Format jobs as a numbered markdown table.

    Args:
        jobs: List of Job objects to format

    Returns:
        Markdown table string with numbered jobs
    """
    lines = []
    lines.append(f"**{len(jobs)} jobs found.** Use # to reference jobs (e.g., 'run job 3'):\n")
    lines.append("| # | Name | Group | Job ID |")
    lines.append("|---|------|-------|--------|")

    for idx, job in enumerate(jobs, start=1):
        group = job.group or "-"
        lines.append(f"| {idx} | {job.name} | {group} | {job.id} |")

    lines.append("\n*Display this table to the user exactly as shown.*")

    return "\n".join(lines)


def _format_job_details(job: Job) -> str:
    """Format job details with options table for display.

    Args:
        job: Job object to format

    Returns:
        Formatted string with job info and options table
    """
    lines = []
    lines.append(f"## {job.name}")
    lines.append("")

    if job.description:
        lines.append(f"{job.description}")
        lines.append("")

    lines.append(f"**Job ID:** `{job.id}`")
    lines.append(f"**Project:** {job.project}")
    if job.group:
        lines.append(f"**Group:** {job.group}")
    lines.append(f"**Enabled:** {'Yes' if job.enabled else 'No'}")
    if job.scheduled:
        lines.append(f"**Scheduled:** {'Yes (enabled)' if job.schedule_enabled else 'Yes (disabled)'}")
    lines.append("")

    # Options table
    if job.options:
        lines.append("### Job Options")
        lines.append("")
        lines.append("| # | Option | Required | Default | Allowed Values |")
        lines.append("|---|--------|----------|---------|----------------|")

        for idx, opt in enumerate(job.options, start=1):
            required = "🔴 Yes" if opt.required else "No"
            default = f"`{opt.value}`" if opt.value else "-"

            if opt.values:
                if len(opt.values) <= 5:
                    allowed = ", ".join(f"`{v}`" for v in opt.values)
                else:
                    allowed = ", ".join(f"`{v}`" for v in opt.values[:3]) + f" ... ({len(opt.values)} total)"
                if opt.enforced:
                    allowed += " *(enforced)*"
            else:
                allowed = "Any"

            lines.append(f"| {idx} | **{opt.name}** | {required} | {default} | {allowed} |")

            # Add description as sub-row if present
            if opt.description:
                lines.append(f"|   | ↳ _{opt.description}_ |   |   |   |")

        lines.append("")

        # Summary of what's needed
        required_opts = [o for o in job.options if o.required and not o.value]
        if required_opts:
            lines.append("**⚠️ Required options (no default):** " + ", ".join(f"`{o.name}`" for o in required_opts))
            lines.append("")
    else:
        lines.append("*This job has no options - it can be run directly.*")
        lines.append("")

    if job.permalink:
        lines.append(f"[View in Rundeck]({job.permalink})")
        lines.append("")

    lines.append("*To run this job, use: run_job with the job_id and required options.*")

    return "\n".join(lines)


def _format_validation_error(job: Job, errors: list[str], provided_options: dict[str, str] | None) -> str:
    """Format validation error with options table for user to provide missing values.

    Args:
        job: The job being executed
        errors: List of validation error messages
        provided_options: Options that were provided (if any)

    Returns:
        Formatted error message with options table
    """
    lines = []
    lines.append(f"## ❌ Cannot run '{job.name}'")
    lines.append("")
    lines.append("**Validation errors:**")
    for err in errors:
        lines.append(f"- {err}")
    lines.append("")

    if job.options:
        lines.append("### Options Required")
        lines.append("")
        lines.append("| Option | Required | Default | Allowed Values | Your Value |")
        lines.append("|--------|----------|---------|----------------|------------|")

        for opt in job.options:
            required = "🔴 **Yes**" if opt.required else "No"
            default = f"`{opt.value}`" if opt.value else "-"
            provided_val = provided_options.get(opt.name) if provided_options else None
            provided = f"`{provided_val}`" if provided_val else "-"

            if opt.values:
                if len(opt.values) <= 4:
                    allowed = ", ".join(f"`{v}`" for v in opt.values)
                else:
                    allowed = ", ".join(f"`{v}`" for v in opt.values[:3]) + f" +{len(opt.values) - 3} more"
                if opt.enforced:
                    allowed += " *(must match)*"
            else:
                allowed = "Any value"

            lines.append(f"| **{opt.name}** | {required} | {default} | {allowed} | {provided} |")

        lines.append("")

    # Clear call to action
    missing_required = [o for o in (job.options or []) if o.required and not o.value]
    if missing_required:
        names = ", ".join(f"`{o.name}`" for o in missing_required)
        lines.append(f"**Please provide values for:** {names}")
        lines.append("")

    lines.append("*Ask the user for the missing option values, then retry with run_job.*")

    return "\n".join(lines)


def _format_run_response(response: JobRunResponse) -> str:
    """Format successful job execution response.

    Args:
        response: The job run response

    Returns:
        Formatted success message
    """
    lines = []
    lines.append(f"## ✅ Job Started: {response.job.name}")
    lines.append("")
    lines.append(f"**Execution ID:** `{response.id}`")
    lines.append(f"**Status:** {response.status}")
    lines.append(f"**Project:** {response.project}")
    lines.append(f"**Started by:** {response.user}")
    if response.argstring:
        lines.append(f"**Options:** `{response.argstring}`")
    lines.append("")
    if response.permalink:
        lines.append(f"[View Execution in Rundeck]({response.permalink})")
        lines.append("")
    lines.append("*Use get_execution to check status, or get_execution_output to view logs.*")

    return "\n".join(lines)


def _parse_job(data: dict[str, Any] | list) -> Job:
    """Parse job data from API response.

    Handles both single job responses (dict) and list responses.
    Converts option data to JobOption models.

    Args:
        data: Raw API response data

    Returns:
        Parsed Job model
    """
    # Handle list response (take first item)
    if isinstance(data, list):
        if not data:
            raise ValueError("Empty job response")
        data = data[0]

    # Parse options if present
    options = None
    if data.get("options"):
        options = [_parse_job_option(opt) for opt in data["options"]]

    return Job(
        id=data["id"],
        name=data["name"],
        group=data.get("group"),
        project=data["project"],
        description=data.get("description"),
        href=data.get("href"),
        permalink=data.get("permalink"),
        scheduled=data.get("scheduled", False),
        schedule_enabled=data.get("scheduleEnabled", True),
        enabled=data.get("enabled", True),
        average_duration=data.get("averageDuration"),
        options=options,
    )


def _parse_job_option(data: dict[str, Any]) -> JobOption:
    """Parse a job option from API response.

    Args:
        data: Raw option data from API

    Returns:
        Parsed JobOption model
    """
    return JobOption(
        name=data["name"],
        description=data.get("description"),
        required=data.get("required", False),
        value=data.get("value"),
        values=data.get("values"),
        enforced=data.get("enforced", False),
        multivalued=data.get("multivalued", False),
        delimiter=data.get("delimiter"),
        secure=data.get("secure", False),
        storage_path=data.get("storagePath"),
        option_type=data.get("type"),
    )


def _parse_run_response(data: dict[str, Any]) -> JobRunResponse:
    """Parse job run response from API.

    Args:
        data: Raw API response data

    Returns:
        Parsed JobRunResponse model
    """
    job_data = data.get("job", {})

    return JobRunResponse(
        id=data["id"],
        href=data["href"],
        permalink=data["permalink"],
        status=data.get("status", "running"),
        project=data["project"],
        job=JobReference(
            id=job_data.get("id", ""),
            name=job_data.get("name", ""),
            group=job_data.get("group"),
            project=job_data.get("project", data["project"]),
            href=job_data.get("href"),
            permalink=job_data.get("permalink"),
        ),
        description=data.get("description"),
        argstring=data.get("argstring"),
        user=data.get("user", "unknown"),
        date_started=data.get("date-started"),
    )
