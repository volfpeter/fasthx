from dataclasses import dataclass, field
from typing import Generic

from fastapi import Request

from .typing import T


@dataclass(frozen=True, slots=True)
class ComponentHeader(Generic[T]):
    """
    Component selector that takes the component key from a request header.

    This class makes it possible for the client to submit the *key/ID* of the required component
    to the server in a header. This component selector will look up the requested component
    factory and return it for rendering.

    If the client doesn't request a specific component, then `default` will be used if it was set,
    otherwise an exception will be raised.

    By default this class treats component keys as case-insensitive. If you'd like to disable
    this behavior, set `case_sensitive` to `True`.

    This component selector also support error rendering.

    Implements:
        - `RequestComponentSelector`.
    """

    header: str
    """The header which is used by the client to communicate the *key* of the requested component."""

    components: dict[str, T]
    """Dictionary that maps errors to component factories."""

    error: type[Exception] | tuple[type[Exception], ...] | None = field(default=None, kw_only=True)
    """The accepted error or errors."""

    default: T | None = field(default=None, kw_only=True)
    """The component factory to use if the client didn't request a specific one."""

    case_sensitive: bool = field(default=False, kw_only=True)
    """Whether the keys of `components` are case-sensitive or not (default is `False`)."""

    def __post_init__(self) -> None:
        if not self.case_sensitive:
            object.__setattr__(
                self,
                "components",
                {k.lower(): v for k, v in self.components.items()},
            )

    def get_component(self, request: Request, error: Exception | None) -> T:
        """
        Returns the component factory to use to render the response.

        If the request doesn't contain a header (with the name `self.header`),
        then `self.default` will be returned if it's not `None`.

        Raises:
            KeyError: If the client request an unknown component or if no component
                was requested and there is no default either.
        """
        if error is not None and (self.error is None or not isinstance(error, self.error)):
            raise error

        if (key := request.headers.get(self.header, None)) is not None:
            if not self.case_sensitive:
                key = key.lower()

            return self.components[key]
        elif self.default is None:
            raise KeyError("Default component factory was not set and header was not found.")
        else:
            return self.default
