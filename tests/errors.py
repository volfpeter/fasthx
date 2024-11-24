from typing import Any

from fastapi import Response


class RenderedError(Exception):
    def __init__(self, data: dict[str, Any], *, response: Response) -> None:
        super().__init__("Data validation failed.")

        # Pattern for setting the response status code for error rendering responses.
        response.status_code = 456

        # Pattern to make the data available in rendering contexts. Not used in tests.
        for key, value in data.items():
            setattr(self, key, value)
