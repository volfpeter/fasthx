import inspect
from collections.abc import Callable
from functools import wraps
from typing import Coroutine

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse

from .dependencies import DependsHXRequest
from .typing import HTMLRenderer, MaybeAsyncFunc, P, T
from .utils import append_to_signature, execute_maybe_sync_func, get_response


def hx(
    render: HTMLRenderer[T], *, no_data: bool = False
) -> Callable[[MaybeAsyncFunc[P, T]], Callable[P, Coroutine[None, None, T | Response]]]:
    """
    Decorator that converts a FastAPI route's return value into HTML if the request was
    an HTMX one.

    Arguments:
        render: The render function converting the route's return value to HTML.
        no_data: If set, the route will only accept HTMX requests.

    Returns:
        The rendered HTML for HTMX requests, otherwise the route's unchanged return value.
    """

    def decorator(func: MaybeAsyncFunc[P, T]) -> Callable[P, Coroutine[None, None, T | Response]]:
        @wraps(func)  # type: ignore[arg-type]
        async def wrapper(
            *args: P.args, __hx_request: DependsHXRequest, **kwargs: P.kwargs
        ) -> T | Response:
            if no_data and __hx_request is None:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST, "This route can only process HTMX requests."
                )

            result = await execute_maybe_sync_func(func, *args, **kwargs)
            if __hx_request is None or isinstance(result, Response):
                return result

            response = get_response(kwargs)
            rendered = await execute_maybe_sync_func(render, result, context=kwargs, request=__hx_request)
            return (
                HTMLResponse(rendered, headers=None if response is None else response.headers)
                if isinstance(rendered, str)
                else rendered
            )

        return append_to_signature(
            wrapper,  # type: ignore[arg-type]
            inspect.Parameter(
                "__hx_request",
                inspect.Parameter.KEYWORD_ONLY,
                annotation=DependsHXRequest,
            ),
        )

    return decorator


def page(
    render: HTMLRenderer[T],
) -> Callable[[MaybeAsyncFunc[P, T]], Callable[P, Coroutine[None, None, Response]]]:
    """
    Decorator that converts a FastAPI route's return value into HTML.

    Arguments:
        render: The render function converting the route's return value to HTML.
    """

    def decorator(func: MaybeAsyncFunc[P, T]) -> Callable[P, Coroutine[None, None, Response]]:
        @wraps(func)  # type: ignore[arg-type]
        async def wrapper(*args: P.args, __page_request: Request, **kwargs: P.kwargs) -> T | Response:
            result = await execute_maybe_sync_func(func, *args, **kwargs)
            if isinstance(result, Response):
                return result

            response = get_response(kwargs)
            rendered: str | Response = await execute_maybe_sync_func(
                render, result, context=kwargs, request=__page_request
            )
            return (
                HTMLResponse(rendered, headers=None if response is None else response.headers)
                if isinstance(rendered, str)
                else rendered
            )

        return append_to_signature(
            wrapper,  # type: ignore[arg-type]
            inspect.Parameter(
                "__page_request",
                inspect.Parameter.KEYWORD_ONLY,
                annotation=Request,
            ),
        )

    return decorator
