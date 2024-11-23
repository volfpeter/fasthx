from typing import Any

import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

from fasthx.htmy import HTMY, ComponentHeader

from .data import (
    DependsRandomNumber,
    User,
    billy,
    billy_json,
    lucy,
    user_list_json,
    users,
)
from .htmy_components import ContextProcessors, HelloWorld, Profile, UserList

billy_html_header = "<h1 >Billy Shears (active=True)</h1>"
billy_html_paragraph = "<p >Billy Shears (active=True)</p>"
billy_html_span = "<span >Billy Shears (active=True)</span>"
user_list_html = "<ul >\n<li >Billy Shears (active=True)</li>\n<li >Lucy (active=True)</li>\n</ul>"


class RenderedError(Exception):
    def __init__(self, data: dict[str, Any], *, response: Response) -> None:
        super().__init__("Data validation failed.")

        # Pattern for setting the response status code for error rendering responses.
        response.status_code = 456

        # Pattern to make the data available in rendering contexts. Not used in tests.
        for key, value in data.items():
            setattr(self, key, value)


@pytest.fixture
def htmy_app() -> FastAPI:  # noqa: C901
    app = FastAPI()

    htmy = HTMY(context_processors=ContextProcessors.all())
    no_data_htmy = HTMY(no_data=True)
    no_data_htmy.context_processors.extend(ContextProcessors.all())

    @app.get("/")
    @htmy.page(UserList)
    def index() -> list[User]:
        return users

    @app.get("/htmx-or-data")
    @htmy.hx(UserList)
    def htmx_or_data(response: Response) -> list[User]:
        response.headers["test-header"] = "exists"
        return users

    @app.get("/htmx-only")
    @htmy.hx(UserList, no_data=True)
    async def htmx_only(random_number: DependsRandomNumber) -> tuple[User, ...]:
        return (billy, lucy)

    @app.get("/htmx-or-data/{id}")
    @htmy.hx(
        ComponentHeader(
            "X-Component",
            {
                "header": Profile.h1,
                "paragraph": Profile.p,
                "hello-world": HelloWorld,
            },
            default=Profile.span,
        )
    )
    def htmx_or_data_by_id(id: int) -> User:
        return billy

    @app.get("/header-with-no-default")
    @htmy.hx(
        ComponentHeader(
            "X-Component",
            {
                "header": Profile.h1,
                "paragraph": Profile.p,
                "span": Profile.span,
            },
        ),
    )
    def header_with_no_default() -> User:
        return billy

    @app.get("/error")  # type: ignore[arg-type]
    @app.get("/error/{kind}")
    @htmy.hx(
        ComponentHeader("X-Component", {}),  # No rendering if there's no exception.
        error_component_selector=ComponentHeader(
            "X-Error-Component",
            {},
            default=HelloWorld,
            error=RenderedError,
        ),
        no_data=True,
    )
    def error(response: Response, kind: str | None = None) -> None:
        if kind:
            # Unhandled error type to see if we get HTTP 500
            raise ValueError(kind)

        raise RenderedError({"a": 1, "b": 2}, response=response)

    @app.get("/error-page")  # type: ignore[arg-type]
    @app.get("/error-page/{kind}")
    @htmy.page(
        ComponentHeader("X-Component", {}),  # No rendering if there's no exception.
        error_component_selector=ComponentHeader(
            "X-Error-Component",
            {},
            default=HelloWorld,
            error=(RenderedError, TypeError, SyntaxError),  # Test error tuple
        ),
    )
    def error_page(response: Response, kind: str | None = None) -> None:
        if kind:
            # Unhandled error type to see if we get HTTP 500
            raise ValueError(kind)

        raise RenderedError({"a": 1, "b": 2}, response=response)

    @app.get("/global-no-data")
    @no_data_htmy.hx(UserList, no_data=False)
    def global_no_data() -> list[User]:
        return []

    return app


@pytest.fixture
def htmy_client(htmy_app: FastAPI) -> TestClient:
    # raise_server_exception must be disabled. Without it, unhandled server
    # errors would result in an exception instead of a HTTP 500 response.
    return TestClient(htmy_app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    ("route", "headers", "status", "expected", "response_headers"),
    (
        # htmy.page() - always renders the HTML result.
        ("/", {"HX-Request": "true"}, 200, user_list_html, {}),
        ("/", None, 200, user_list_html, {}),
        ("/", {"HX-Request": "false"}, 200, user_list_html, {}),
        # htmy.hx() - returns JSON for non-HTMX requests.
        ("/htmx-or-data", {"HX-Request": "true"}, 200, user_list_html, {"test-header": "exists"}),
        ("/htmx-or-data", None, 200, user_list_json, {"test-header": "exists"}),
        ("/htmx-or-data", {"HX-Request": "false"}, 200, user_list_json, {"test-header": "exists"}),
        ("/htmx-or-data/1", None, 200, billy_json, {}),
        ("/htmx-or-data/2", {"HX-Request": "true"}, 200, billy_html_span, {}),
        ("/htmx-or-data/3", {"HX-Request": "true", "X-Component": "header"}, 200, billy_html_header, {}),
        ("/htmx-or-data/3", {"HX-Request": "true", "X-Component": "hello-world"}, 200, "Hello World!", {}),
        (
            "/htmx-or-data/3",
            {"HX-Request": "true", "X-Component": "HeAdEr"},  # Test case-sensitivity.
            200,
            billy_html_header,
            {},
        ),
        (
            "/htmx-or-data/4",
            {"HX-Request": "true", "X-Component": "paragraph"},
            200,
            billy_html_paragraph,
            {},
        ),
        ("/htmx-or-data/5", {"HX-Request": "true", "X-Component": "non-existent"}, 500, "", {}),
        (
            "/header-with-no-default",
            {"HX-Request": "true", "X-Component": "header"},
            200,
            billy_html_header,
            {},
        ),
        (
            "/header-with-no-default",
            {"HX-Request": "true", "X-Component": "paragraph"},
            200,
            billy_html_paragraph,
            {},
        ),
        (
            "/header-with-no-default",
            {"HX-Request": "true", "X-Component": "span"},
            200,
            billy_html_span,
            {},
        ),
        ("/header-with-no-default", {"HX-Request": "true"}, 500, "", {}),
        # htmy.hx(no_data=True) - raises exception for non-HTMX requests.
        ("/htmx-only", {"HX-Request": "true"}, 200, user_list_html, {}),
        ("/htmx-only", None, 400, "", {}),
        ("/htmx-only", {"HX-Request": "false"}, 400, "", {}),
        # hx() error rendering
        ("/error", {"HX-Request": "true"}, 456, "Hello World!", {}),
        ("/error/value-error", {"HX-Request": "true"}, 500, "", {}),
        # page() error rendering
        ("/error-page", None, 456, "Hello World!", {}),
        ("/error-page/value-error", None, 500, "None", {}),
        # Globally disabled data responses
        ("/global-no-data", None, 400, "", {}),
    ),
)
def test_htmy(
    htmy_client: TestClient,
    route: str,
    headers: dict[str, str] | None,
    status: int,
    expected: str,
    response_headers: dict[str, str],
) -> None:
    response = htmy_client.get(route, headers=headers)
    assert response.status_code == status
    if status >= 400:
        return

    result = response.text
    assert result == expected

    assert all((response.headers.get(key) == value) for key, value in response_headers.items())
