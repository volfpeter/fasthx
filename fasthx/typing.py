from collections.abc import Callable, Coroutine
from typing import Any, ParamSpec, Protocol, TypeAlias, TypeVar, runtime_checkable

from fastapi import Request, Response

P = ParamSpec("P")
T = TypeVar("T")
Tcontra = TypeVar("Tcontra", contravariant=True)

MaybeAsyncFunc = Callable[P, T] | Callable[P, Coroutine[Any, Any, T]]


class SyncHTMLRenderer(Protocol[Tcontra]):
    """Sync HTML renderer definition."""

    def __call__(self, result: Tcontra, *, context: dict[str, Any], request: Request) -> str | Response:
        """
        Arguments:
            result: The result of the route the renderer is used on.
            context: Every keyword argument the route received.
            request: The request being served.

        Returns:
            HTML string (it will be automatically converted to `HTMLResponse`) or a `Response` object.
        """
        ...


class AsyncHTMLRenderer(Protocol[Tcontra]):
    """Async HTML renderer definition."""

    async def __call__(
        self, result: Tcontra, *, context: dict[str, Any], request: Request
    ) -> str | Response:
        """
        Arguments:
            result: The result of the route the renderer is used on.
            context: Every keyword argument the route received.
            request: The request being served.

        Returns:
            HTML string (it will be automatically converted to `HTMLResponse`) or a `Response` object.
        """
        ...


HTMLRenderer = SyncHTMLRenderer[Tcontra] | AsyncHTMLRenderer[Tcontra]
"""Sync or async HTML renderer type."""


class JinjaContextFactory(Protocol):
    """
    Protocol definition for methods that convert a FastAPI route's result and route context
    (i.e. the route's arguments) into a Jinja context (`dict`).
    """

    def __call__(self, *, route_result: Any, route_context: dict[str, Any]) -> dict[str, Any]:
        """
        Arguments:
            route_result: The result of the route.
            route_context: Every keyword argument the route received.

        Returns:
            The Jinja context dictionary.

        Raises:
            ValueError: If converting the arguments to a Jinja context fails.
        """
        ...


@runtime_checkable
class RequestComponentSelector(Protocol):
    """
    Component selector protocol that loads the required component's ID from the request.

    The protocol is runtime-checkable, so it can be used in `isinstance()`, `issubclass()` calls.
    """

    def get_component_id(self, request: Request) -> str:
        """
        Returns the identifier of the component that was requested by the client.

        Raises:
            KeyError: If the component couldn't be identified.
        """
        ...


ComponentSelector: TypeAlias = str | RequestComponentSelector
"""Type alias for known component selectors."""
