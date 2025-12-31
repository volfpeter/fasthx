import inspect
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Literal, TypeAlias, cast, overload

from fastapi import HTTPException, Response, status
from fastapi.responses import HTMLResponse, StreamingResponse

from .dependencies import DependsHXRequest, DependsPageRequest
from .typing import MaybeAsyncFunc, P, RenderFunction, StreamingRenderFunction, T
from .utils import append_to_signature, execute_maybe_sync_func, get_response

# -- Rendering decorators

HXReturnType: TypeAlias = Callable[
    [MaybeAsyncFunc[P, T | Response]], Callable[P, Coroutine[None, None, T | Response]]
]


@overload
def hx(
    render: StreamingRenderFunction[T],
    *,
    no_data: bool = False,
    render_error: StreamingRenderFunction[Exception] | None = None,
    stream: Literal[True],
) -> HXReturnType[P, T]: ...


@overload
def hx(
    render: RenderFunction[T],
    *,
    no_data: bool = False,
    render_error: RenderFunction[Exception] | None = None,
    stream: Literal[False] = False,
) -> HXReturnType[P, T]: ...


def hx(
    render: RenderFunction[T] | StreamingRenderFunction[T],
    *,
    no_data: bool = False,
    render_error: RenderFunction[Exception] | StreamingRenderFunction[Exception] | None = None,
    stream: bool = False,
) -> HXReturnType[P, T]:
    """
    Decorator that converts a FastAPI route's return value into HTML if the request was
    an HTMX one.

    Arguments:
        render: The render function converting the route's return value to HTML.
        no_data: If set, the route will only accept HTMX requests.
        render_error: Optional render function for handling exceptions raised by the decorated route.
            If not `None`, it is expected to raise an error if the exception can not be rendered.
        stream: If set, the route will stream the response. `render` (and `render_error` if not `None`)
            must be a `StreamingRenderFunction` in that case.

    Returns:
        The rendered HTML for HTMX requests, otherwise the route's unchanged return value.
    """

    def decorator(
        func: MaybeAsyncFunc[P, T | Response],
    ) -> Callable[P, Coroutine[None, None, T | Response]]:
        @wraps(func)
        async def wrapper(
            __hx_request: DependsHXRequest, *args: P.args, **kwargs: P.kwargs
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
            if stream:
                renderer = cast(StreamingRenderFunction[T | Exception], renderer)
                content_stream = renderer(result, context=kwargs, request=__hx_request)

                return StreamingResponse(
                    content_stream,
                    # The default status code of the FastAPI Response dependency is None
                    # (not allowed by the typing but required for FastAPI).
                    status_code=getattr(response, "status_code", 200) or 200,
                    headers=getattr(response, "headers", None),
                    media_type="text/html",
                    background=getattr(response, "background", None),
                )
            else:
                renderer = cast(RenderFunction[T | Exception], renderer)
                rendered: str = await execute_maybe_sync_func(
                    renderer, result, context=kwargs, request=__hx_request
                )

                return HTMLResponse(
                    rendered,
                    # The default status code of the FastAPI Response dependency is None
                    # (not allowed by the typing but required for FastAPI).
                    status_code=getattr(response, "status_code", 200) or 200,
                    headers=getattr(response, "headers", None),
                    background=getattr(response, "background", None),
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


PageReturnType: TypeAlias = Callable[
    [MaybeAsyncFunc[P, T | Response]], Callable[P, Coroutine[None, None, Response]]
]


@overload
def page(
    render: StreamingRenderFunction[T],
    *,
    render_error: StreamingRenderFunction[Exception] | None = None,
    stream: Literal[True],
) -> PageReturnType[P, T]: ...


@overload
def page(
    render: RenderFunction[T],
    *,
    render_error: RenderFunction[Exception] | None = None,
    stream: Literal[False] = False,
) -> PageReturnType[P, T]: ...


def page(
    render: RenderFunction[T] | StreamingRenderFunction[T],
    *,
    render_error: RenderFunction[Exception] | StreamingRenderFunction[Exception] | None = None,
    stream: bool = False,
) -> PageReturnType[P, T]:
    """
    Decorator that converts a FastAPI route's return value into HTML.

    Arguments:
        render: The render function converting the route's return value to HTML.
        render_error: Optional render function for handling exceptions raised by the decorated route.
            If not `None`, it is expected to raise an error if the exception can not be rendered.
        stream: If set, the route will stream the response. `render` (and `render_error` if not `None`)
            must be a `StreamingRenderFunction` in that case.
    """

    def decorator(func: MaybeAsyncFunc[P, T | Response]) -> Callable[P, Coroutine[None, None, Response]]:
        @wraps(func)
        async def wrapper(
            __page_request: DependsPageRequest, *args: P.args, **kwargs: P.kwargs
        ) -> Response:
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

            if stream:
                renderer = cast(StreamingRenderFunction[T | Exception], renderer)
                content_stream = renderer(result, context=kwargs, request=__page_request)

                return StreamingResponse(
                    content_stream,
                    # The default status code of the FastAPI Response dependency is None
                    # (not allowed by the typing but required for FastAPI).
                    status_code=getattr(response, "status_code", 200) or 200,
                    headers=getattr(response, "headers", None),
                    media_type="text/html",
                    background=getattr(response, "background", None),
                )
            else:
                renderer = cast(RenderFunction[T | Exception], renderer)
                rendered = await execute_maybe_sync_func(
                    renderer, result, context=kwargs, request=__page_request
                )

                return HTMLResponse(
                    rendered,
                    # The default status code of the FastAPI Response dependency is None
                    # (not allowed by the typing but required for FastAPI).
                    status_code=getattr(response, "status_code", 200) or 200,
                    headers=getattr(response, "headers", None),
                    background=getattr(response, "background", None),
                )

        return append_to_signature(
            wrapper,  # type: ignore[arg-type]
            inspect.Parameter(
                "__page_request",
                inspect.Parameter.KEYWORD_ONLY,
                annotation=DependsPageRequest,
            ),
            # Override the return annotation to Response to prevent FastAPI from
            # trying to resolve the return type, it will be converted to a Response
            # object anyway.
            return_annotation=Response,
        )

    return decorator
