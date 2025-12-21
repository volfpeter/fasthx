from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any, ParamSpec, Protocol, TypeAlias, TypeVar, runtime_checkable

if TYPE_CHECKING:
    from fastapi import Request
    from starlette.responses import ContentStream


P = ParamSpec("P")
T = TypeVar("T")
Tco = TypeVar("Tco", covariant=True)
Tcontra = TypeVar("Tcontra", contravariant=True)

MaybeAsyncFunc: TypeAlias = Callable[P, T] | Callable[P, Coroutine[Any, Any, T]]


class SyncRenderFunction(Protocol[Tcontra]):
    """Sync render function definition."""

    def __call__(self, result: Tcontra, *, context: dict[str, Any], request: Request) -> str:
        """
        Arguments:
            result: The result of the route the renderer is used on.
            context: Every keyword argument the route received.
            request: The request being served.

        Returns:
            The rendered string.
        """
        ...


class AsyncRenderFunction(Protocol[Tcontra]):
    """Async render function definition."""

    async def __call__(self, result: Tcontra, *, context: dict[str, Any], request: Request) -> str:
        """
        Arguments:
            result: The result of the route the renderer is used on.
            context: Every keyword argument the route received.
            request: The request being served.

        Returns:
            The rendered string.
        """
        ...


RenderFunction: TypeAlias = SyncRenderFunction[Tcontra] | AsyncRenderFunction[Tcontra]
"""Sync or async render function type."""


class StreamingRenderFunction(Protocol[Tcontra]):
    """Streaming render function definition that produces a content stream."""

    def __call__(self, result: Tcontra, *, context: dict[str, Any], request: Request) -> ContentStream:
        """
        Arguments:
            result: The result of the route the renderer is used on.
            context: Every keyword argument the route received.
            request: The request being served.

        Returns:
            An async generator that yields HTML string chunks.
        """
        ...


@runtime_checkable
class RequestComponentSelector(Protocol[Tco]):
    """
    Component selector protocol that uses the request to select the component that will be rendered.

    The protocol is runtime-checkable, so it can be used in `isinstance()`, `issubclass()` calls.
    """

    def get_component(self, request: Request, error: Exception | None) -> Tco:
        """
        Returns the component that was requested by the client.

        The caller should ensure that `error` will be the exception that was raised by the
        route or `None` if the route returned normally.

        If an implementation can not or does not want to handle route errors, then the method
        should re-raise the received exception. Example:

        ```python
        class MyComponentSelector:
            def get_component(self, request: Request, error: Exception | None) -> str:
                if error is not None:
                    raise error

                ...
        ```

        Raises:
            KeyError: If the component couldn't be identified.
            Exception: The received `error` argument if it was not `None` and the implementation
                can not handle route errors.
        """
        ...


ComponentSelector: TypeAlias = T | RequestComponentSelector[T]
"""Type alias for all types of component selectors."""
