import inspect
from collections.abc import Callable
from functools import wraps
from typing import Coroutine

from fastapi import HTTPException, Response, status
from fastapi.responses import HTMLResponse

from .dependencies import DependsHXRequest, DependsPageRequest
from .typing import HTMLRenderer, MaybeAsyncFunc, P, T
from .utils import append_to_signature, execute_maybe_sync_func, get_response


def hx(
    render: HTMLRenderer[T],
    *,
    no_data: bool = False,
    render_error: HTMLRenderer[Exception] | None = None,
) -> Callable[[MaybeAsyncFunc[P, T]], Callable[P, Coroutine[None, None, T | Response]]]:
    """
    Decorator that converts a FastAPI route's return value into HTML if the request was
    an HTMX one.

    Arguments:
        render: The render function converting the route's return value to HTML.
        no_data: If set, the route will only accept HTMX requests.
        render_error: Optional render function for handling exceptions raised by the decorated route.
            If not `None`, it is expected to raise an error if the exception can not be rendered.

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

            try:
                result = await execute_maybe_sync_func(func, *args, **kwargs)
                renderer = render
            except Exception as e:
                # Reraise if not HX request, because the checks later don't differentiate between
                # error and non-error result objects.
                if render_error is None or __hx_request is None:
                    raise e

                result = e  # type: ignore[assignment]
                renderer = render_error  # type: ignore[assignment]

            if __hx_request is None or isinstance(result, Response):
                return result

            response = get_response(kwargs)
            rendered = await execute_maybe_sync_func(renderer, result, context=kwargs, request=__hx_request)

            return (
                HTMLResponse(
                    rendered,
                    # The default status code of the FastAPI Response dependency is None
                    # (not allowed by the typing but required for FastAPI).
                    status_code=getattr(response, "status_code", 200) or 200,
                    headers=getattr(response, "headers", None),
                    background=getattr(response, "background", None),
                )
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
    *,
    render_error: HTMLRenderer[Exception] | None = None,
) -> Callable[[MaybeAsyncFunc[P, T]], Callable[P, Coroutine[None, None, Response]]]:
    """
    Decorator that converts a FastAPI route's return value into HTML.

    Arguments:
        render: The render function converting the route's return value to HTML.
        render_error: Optional render function for handling exceptions raised by the decorated route.
            If not `None`, it is expected to raise an error if the exception can not be rendered.
    """

    def decorator(func: MaybeAsyncFunc[P, T]) -> Callable[P, Coroutine[None, None, Response]]:
        @wraps(func)  # type: ignore[arg-type]
        async def wrapper(
            *args: P.args, __page_request: DependsPageRequest, **kwargs: P.kwargs
        ) -> T | Response:
            try:
                result = await execute_maybe_sync_func(func, *args, **kwargs)
                renderer = render
            except Exception as e:
                if render_error is None:
                    raise e

                result = e  # type: ignore[assignment]
                renderer = render_error  # type: ignore[assignment]

            if isinstance(result, Response):
                return result

            response = get_response(kwargs)
            rendered = await execute_maybe_sync_func(
                renderer, result, context=kwargs, request=__page_request
            )
            return (
                HTMLResponse(
                    rendered,
                    # The default status code of the FastAPI Response dependency is None
                    # (not allowed by the typing but required for FastAPI).
                    status_code=getattr(response, "status_code", 200) or 200,
                    headers=getattr(response, "headers", None),
                    background=getattr(response, "background", None),
                )
                if isinstance(rendered, str)
                else rendered
            )

        return append_to_signature(
            wrapper,  # type: ignore[arg-type]
            inspect.Parameter(
                "__page_request",
                inspect.Parameter.KEYWORD_ONLY,
                annotation=DependsPageRequest,
            ),
        )

    return decorator
