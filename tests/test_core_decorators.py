from typing import Any

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from fasthx import hx, page

from .data import DependsRandomNumber, User, user_list_html, user_list_json, users


def render_user_list(result: list[User], *, context: dict[str, Any], request: Request) -> str:
    # Test that the value of the DependsRandomNumber dependency is in the context.
    random_number = context["random_number"]
    assert random_number == 4

    return "".join(("<ul>", *(f"<li>{u.name} (active={u.active})</li>" for u in result), "</ul>"))


async def async_render_user_list(result: list[User], *, context: dict[str, Any], request: Request) -> str:
    return render_user_list(result, context=context, request=request)


class DataError(Exception):
    def __init__(self, message: str, response: Response) -> None:
        self.message = message
        # Highlight how to set the response code for a route that has error rendering.
        response.status_code = 499


def render_data_error(result: Exception, *, context: dict[str, Any], request: Request) -> str:
    if isinstance(result, DataError):
        return f'<DataError message="{result.message}" />'

    raise result


@pytest.fixture
def hx_app() -> FastAPI:  # noqa: C901
    app = FastAPI()

    @app.get("/")
    @page(render_user_list)
    def index(random_number: DependsRandomNumber) -> list[User]:
        return users

    @app.get("/htmx-or-data")
    @hx(render_user_list)
    def htmx_or_data(random_number: DependsRandomNumber, response: Response) -> list[User]:
        response.headers["test-header"] = "exists"
        return users

    # There's a strange mypy issue here, it finds errors for the routes that defined later,
    # regardless of the order. It seems it fails to resolve and match generic types.

    @app.get("/htmx-only")  # type: ignore
    @hx(async_render_user_list, no_data=True)
    async def htmx_only(random_number: DependsRandomNumber) -> list[User]:
        return users

    @app.get("/error/{kind}")  # type: ignore
    @hx(render_user_list, render_error=render_data_error)
    def error_in_route(kind: str, response: Response) -> list[User]:
        if kind == "data":
            raise DataError("test-message", response)
        elif kind == "value":
            raise ValueError("Value error was requested.")

        return users

    @app.get("/error-no-data/{kind}")  # type: ignore
    @hx(render_user_list, render_error=render_data_error, no_data=True)
    def error_in_route_no_data(kind: str, response: Response) -> list[User]:
        if kind == "data":
            raise DataError("test-message", response)
        elif kind == "value":
            raise ValueError("Value error was requested.")

        return users

    @app.get("/error-page/{kind}")  # type: ignore
    @page(render_user_list, render_error=render_data_error)
    def error_in_route_page(kind: str, response: Response) -> list[User]:
        if kind == "data":
            raise DataError("test-message", response)
        elif kind == "value":
            raise ValueError("Value error was requested.")

        return users

    return app


@pytest.fixture
def hx_client(hx_app: FastAPI) -> TestClient:
    return TestClient(hx_app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    ("route", "headers", "status", "expected", "response_headers"),
    (
        # page() - always renders the HTML result.
        ("/", {"HX-Request": "true"}, 200, user_list_html, {}),
        ("/", None, 200, user_list_html, {}),
        ("/", {"HX-Request": "false"}, 200, user_list_html, {}),
        # hx() - returns JSON for non-HTMX requests.
        ("/htmx-or-data", {"HX-Request": "true"}, 200, user_list_html, {"test-header": "exists"}),
        ("/htmx-or-data", None, 200, user_list_json, {"test-header": "exists"}),
        ("/htmx-or-data", {"HX-Request": "false"}, 200, user_list_json, {"test-header": "exists"}),
        # hy(no_data=True) - raises exception for non-HTMX requests.
        ("/htmx-only", {"HX-Request": "true"}, 200, user_list_html, {}),
        ("/htmx-only", None, 400, "", {}),
        ("/htmx-only", {"HX-Request": "false"}, 400, "", {}),
    ),
)
def test_hx_and_page(
    hx_client: TestClient,
    route: str,
    headers: dict[str, str] | None,
    status: int,
    expected: str,
    response_headers: dict[str, str],
) -> None:
    response = hx_client.get(route, headers=headers)
    assert response.status_code == status
    if status == 400:
        return

    result = response.text
    assert result == expected

    assert all((response.headers.get(key) == value) for key, value in response_headers.items())


@pytest.mark.parametrize(
    ("route", "headers", "status", "expected"),
    (
        ("/error/data", {"HX-Request": "true"}, 499, '<DataError message="test-message" />'),
        ("/error/data", None, 500, None),  # No rendering, internal server error
        ("/error/value", {"HX-Request": "true"}, 500, None),  # No rendering for value route
        ("/error-no-data/data", {"HX-Request": "true"}, 499, '<DataError message="test-message" />'),
        ("/error-no-data/data", None, 400, None),  # No data, bad request
        ("/error-no-data/value", {"HX-Request": "true"}, 500, None),  # No rendering for value route
        ("/error-page/data", {"HX-Request": "true"}, 499, '<DataError message="test-message" />'),
        ("/error-page/data", None, 499, '<DataError message="test-message" />'),  # Rendering non-HX request
        ("/error-page/value", {"HX-Request": "true"}, 500, None),  # No rendering for value route
    ),
)
def test_hx_and_page_error_rendering(
    hx_client: TestClient,
    route: str,
    headers: dict[str, str] | None,
    status: int,
    expected: str | None,
) -> None:
    response = hx_client.get(route, headers=headers)
    assert response.status_code == status
    if expected is not None:
        assert response.text == expected
