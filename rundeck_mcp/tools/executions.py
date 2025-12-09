from typing import Any

from rundeck_mcp.client import get_client
from rundeck_mcp.models import (
    Execution,
    ExecutionOutput,
    ExecutionQuery,
    ListResponseModel,
    LogEntry,
)
from rundeck_mcp.models.jobs import JobReference


def list_executions(query: ExecutionQuery) -> ListResponseModel[Execution]:
    """List job executions with optional filtering.

    Returns a list of executions matching the specified criteria. Filter by
    project, job_id, status, or time range. Results are ordered by start time
    (most recent first).

    Args:
        query: Query parameters for filtering executions

    Returns:
        List of Execution objects matching the query

    Examples:
        List recent executions in a project:
        >>> result = list_executions(ExecutionQuery(project="myproject"))

        List failed executions for a specific job:
        >>> result = list_executions(ExecutionQuery(
        ...     job_id="abc-123-def",
        ...     status="failed"
        ... ))

        List executions from the last hour:
        >>> result = list_executions(ExecutionQuery(
        ...     project="myproject",
        ...     recent_filter="1h"
        ... ))
    """
    client = get_client()
    params = query.to_params()

    # Use job-specific endpoint if job_id is provided
    if query.job_id:
        response = client.get(f"/job/{query.job_id}/executions", params=params)
    elif query.project:
        response = client.get(f"/project/{query.project}/executions", params=params)
    else:
        raise ValueError("Either project or job_id must be provided")

    # Handle response format (executions are nested in 'executions' key)
    executions_data = response.get("executions", []) if isinstance(response, dict) else response

    executions = [_parse_execution(exec_data) for exec_data in executions_data]
    return ListResponseModel[Execution](response=executions)


def get_execution(execution_id: int) -> Execution:
    """Get detailed information about a specific execution.

    Returns the full execution details including status, timing, node results,
    and the arguments used.

    Args:
        execution_id: The execution ID (integer)

    Returns:
        Execution object with full details

    Examples:
        >>> execution = get_execution(12345)
        >>> print(execution.status)
        'succeeded'
        >>> print(execution.duration_seconds)
        45.2
    """
    client = get_client()
    response = client.get(f"/execution/{execution_id}")

    return _parse_execution(response)


def get_execution_output(
    execution_id: int,
    last_lines: int | None = None,
    max_lines: int | None = None,
    offset: int | None = None,
    node: str | None = None,
) -> ExecutionOutput:
    """Get the log output from a job execution.

    Retrieves log entries from the execution. For running executions, use the
    'offset' parameter to poll for new output. The 'completed' field indicates
    whether the execution has finished.

    Args:
        execution_id: The execution ID (integer)
        last_lines: Return only the last N lines (overrides offset)
        max_lines: Maximum number of lines to return from offset
        offset: Byte offset to start reading from (for tailing)
        node: Filter output to a specific node

    Returns:
        ExecutionOutput with log entries and metadata

    Examples:
        Get all output:
        >>> output = get_execution_output(12345)
        >>> for entry in output.entries:
        ...     print(f"[{entry.level}] {entry.log}")

        Get last 50 lines:
        >>> output = get_execution_output(12345, last_lines=50)

        Tail running execution:
        >>> output = get_execution_output(12345, offset=0)
        >>> while not output.completed:
        ...     output = get_execution_output(12345, offset=output.offset)
        ...     # process new entries
    """
    client = get_client()

    # Build path with optional node filter
    path = f"/execution/{execution_id}/output"
    if node:
        path = f"/execution/{execution_id}/output/node/{node}"

    # Build parameters
    params: dict[str, Any] = {}
    if last_lines is not None:
        params["lastlines"] = last_lines
    if max_lines is not None:
        params["maxlines"] = max_lines
    if offset is not None:
        params["offset"] = offset

    response = client.get(path, params=params)

    return _parse_execution_output(execution_id, response)


def _parse_execution(data: dict[str, Any]) -> Execution:
    """Parse execution data from API response.

    Args:
        data: Raw API response data

    Returns:
        Parsed Execution model
    """
    # Parse job reference if present
    job_data = data.get("job")
    job_ref = None
    if job_data:
        job_ref = JobReference(
            id=job_data.get("id", ""),
            name=job_data.get("name", ""),
            group=job_data.get("group"),
            project=job_data.get("project", data.get("project", "")),
            href=job_data.get("href"),
            permalink=job_data.get("permalink"),
        )

    return Execution(
        id=data["id"],
        href=data.get("href"),
        permalink=data.get("permalink"),
        status=data.get("status", "running"),
        project=data.get("project", ""),
        job=job_ref,
        user=data.get("user", "unknown"),
        date_started=data.get("date-started"),
        date_ended=data.get("date-ended"),
        argstring=data.get("argstring"),
        description=data.get("description"),
        successful_nodes=data.get("successfulNodes"),
        failed_nodes=data.get("failedNodes"),
    )


def _parse_execution_output(execution_id: int, data: dict[str, Any]) -> ExecutionOutput:
    """Parse execution output data from API response.

    Args:
        execution_id: The execution ID
        data: Raw API response data

    Returns:
        Parsed ExecutionOutput model
    """
    # Parse log entries
    entries_data = data.get("entries", [])
    entries = [_parse_log_entry(entry) for entry in entries_data]

    return ExecutionOutput(
        id=execution_id,
        offset=data.get("offset", 0),
        completed=data.get("completed", False),
        exec_completed=data.get("execCompleted", False),
        has_more_output=data.get("hasMoreOutput", False),
        exec_state=data.get("execState"),
        exec_duration=data.get("execDuration"),
        percent_loaded=data.get("percentLoaded"),
        total_size=data.get("totalSize"),
        entries=entries,
    )


def _parse_log_entry(data: dict[str, Any]) -> LogEntry:
    """Parse a log entry from API response.

    Args:
        data: Raw log entry data

    Returns:
        Parsed LogEntry model
    """
    return LogEntry(
        time=data.get("time"),
        absolute_time=data.get("absolute_time"),
        level=data.get("level", "NORMAL"),
        log=data.get("log", ""),
        node=data.get("node"),
        step=data.get("stepctx"),
        user=data.get("user"),
    )
