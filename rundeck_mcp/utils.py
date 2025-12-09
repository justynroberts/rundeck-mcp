from rundeck_mcp.client import get_client
from rundeck_mcp.models import MCPContext


def get_mcp_context() -> MCPContext:
    """Get MCP Context.

    Creates the context object with server connection information.
    This is called during server startup via the lifespan context manager.

    Returns:
        MCPContext with server configuration
    """
    client = get_client()
    return MCPContext(
        server_url=client.base_url,
        api_version=client.api_version,
    )


def validate_job_options(
    job_options: list[dict] | None,
    provided_options: dict[str, str] | None,
) -> tuple[bool, list[str]]:
    """Validate provided options against job option definitions.

    Checks that:
    - All required options are provided
    - Values for enforced options are from the allowed list
    - No unknown options are provided

    Args:
        job_options: List of job option definitions from the job
        provided_options: Options provided for execution

    Returns:
        Tuple of (is_valid, list_of_error_messages)
    """
    errors: list[str] = []
    provided = provided_options or {}

    if not job_options:
        if provided:
            errors.append(f"Job has no options, but options were provided: {list(provided.keys())}")
        return len(errors) == 0, errors

    option_map = {opt["name"]: opt for opt in job_options}
    option_names = set(option_map.keys())

    # Check for unknown options
    unknown = set(provided.keys()) - option_names
    if unknown:
        errors.append(f"Unknown options: {sorted(unknown)}. Valid options: {sorted(option_names)}")

    # Check required options
    for opt in job_options:
        name = opt["name"]
        required = opt.get("required", False)
        default = opt.get("value")

        if required and name not in provided and not default:
            errors.append(f"Required option '{name}' is missing")

    # Check enforced values
    for name, value in provided.items():
        if name not in option_map:
            continue

        opt = option_map[name]
        allowed_values = opt.get("values")
        enforced = opt.get("enforced", False)

        if enforced and allowed_values and value not in allowed_values:
            errors.append(f"Option '{name}' value '{value}' is not in allowed values: {allowed_values}")

    return len(errors) == 0, errors


def format_job_options_for_display(job_options: list[dict] | None) -> str:
    """Format job options for human-readable display.

    Creates a formatted string showing all options with their properties
    including required status, defaults, and allowed values.

    Args:
        job_options: List of job option definitions

    Returns:
        Formatted string for display
    """
    if not job_options:
        return "This job has no options."

    lines = ["Job Options:", ""]

    for opt in job_options:
        name = opt.get("name", "unknown")
        required = opt.get("required", False)
        default = opt.get("value")
        description = opt.get("description", "")
        allowed_values = opt.get("values")
        enforced = opt.get("enforced", False)
        secure = opt.get("secure", False)

        # Build option line
        marker = "[REQUIRED]" if required else "[optional]"
        line = f"  - {name} {marker}"

        if secure:
            line += " [SECURE]"

        if default:
            line += f" (default: '{default}')"

        lines.append(line)

        if description:
            lines.append(f"      {description}")

        if allowed_values:
            enforcement = "must be" if enforced else "suggested"
            values_str = ", ".join(f"'{v}'" for v in allowed_values[:10])
            if len(allowed_values) > 10:
                values_str += f" ... ({len(allowed_values)} total)"
            lines.append(f"      Allowed values ({enforcement}): {values_str}")

        lines.append("")

    return "\n".join(lines)
