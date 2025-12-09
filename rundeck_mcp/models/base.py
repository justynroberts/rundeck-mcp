from typing import TypeVar

from pydantic import BaseModel, computed_field

DEFAULT_PAGINATION_LIMIT = 20
MAXIMUM_PAGINATION_LIMIT = 100
MAX_RESULTS = 1000

T = TypeVar("T", bound=BaseModel)


class ListResponseModel[T: BaseModel](BaseModel):
    """List response model.

    This model wraps responses from list requests to include additional metadata
    that helps the agent interpret the response. It is generic so it can be used
    with any entity type (e.g., Job, Execution, etc.).
    """

    response: list[T]

    @computed_field
    @property
    def response_summary(self) -> str:
        """Generate a summary of the response."""
        count = len(self.response)
        entity_type = self.response[0].__class__.__name__ if self.response else "Unknown"
        summary = [
            f"ListResponseModel<{entity_type}>:",
            f"- Returned {count} record(s) of type '{entity_type}'.",
        ]
        if count == MAX_RESULTS:
            summary.append(
                "- WARNING: The number of records equals the response limit. There may be more"
                " records not included in this response."
            )
        return "\n".join(summary)
