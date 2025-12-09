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
from rundeck_mcp.utils import format_job_options_for_display, validate_job_options


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


def get_job(job_id: str) -> Job:
    """Get detailed information about a specific job.

    Returns the full job definition including all options, their default values,
    allowed values, and whether they are required.

    Args:
        job_id: The job UUID

    Returns:
        Job object with full details including options

    Examples:
        >>> job = get_job("abc-123-def")
        >>> print(job.name)
        'Deploy Application'
        >>> print(job.options_summary)
        'Job Options: - version [REQUIRED]...'
    """
    client = get_client()
    response = client.get(f"/job/{job_id}")

    return _parse_job(response)


def run_job(job_id: str, request: JobRunRequest | None = None) -> JobRunResponse:
    """Execute a Rundeck job with optional parameters.

    Before running, this tool validates that:
    - All required options are provided (or have defaults)
    - Option values match allowed values for enforced options

    If validation fails, returns an error with details about what's missing
    or invalid, along with the job's option definitions to help correct the request.

    Args:
        job_id: The job UUID to execute
        request: Optional execution parameters including options

    Returns:
        JobRunResponse with execution ID and status

    Raises:
        ValueError: If required options are missing or values are invalid

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
    job_options = job_response.get("options") if isinstance(job_response, dict) else None

    provided_options = request.options if request else None

    # Validate options
    is_valid, errors = validate_job_options(job_options, provided_options)

    if not is_valid:
        options_help = format_job_options_for_display(job_options)
        error_msg = "Job execution validation failed:\n"
        error_msg += "\n".join(f"  - {e}" for e in errors)
        error_msg += f"\n\n{options_help}"
        raise ValueError(error_msg)

    # Build request body
    body = request.to_request_body() if request else {}

    # Execute job
    response = client.post(f"/job/{job_id}/run", json=body)

    return _parse_run_response(response)


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
