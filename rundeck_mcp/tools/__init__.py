from .executions import (
    get_execution,
    get_execution_output,
    list_executions,
)
from .jobs import (
    get_job,
    list_jobs,
    run_job,
)

# Read-only tools (safe, non-destructive operations)
read_tools = [
    # Jobs
    list_jobs,
    get_job,
    # Executions
    list_executions,
    get_execution,
    get_execution_output,
]

# Write tools (potentially dangerous operations that modify state)
write_tools = [
    # Jobs
    run_job,
]

# All tools (combined list for backward compatibility)
all_tools = read_tools + write_tools
