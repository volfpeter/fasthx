import pytest
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
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
from .errors import RenderedError
from .htmy_components import HelloWorld, Profile, RequestProcessors, UserList, UserListItem

billy_html_header = "<h1 >Billy Shears (active=True)</h1>"
billy_html_paragraph = "<p >Billy Shears (active=True)</p>"
billy_html_span = "<span >Billy Shears (active=True)</span>"
user_list_html = "<ul >\n<li >Billy Shears (active=True)</li>\n<li >Lucy (active=True)</li>\n</ul>"


@pytest.fixture
def htmy_app() -> FastAPI:  # noqa: C901
    app = FastAPI()

    htmy = HTMY(request_processors=RequestProcessors.all())
    no_data_htmy = HTMY(no_data=True)
    no_data_htmy.request_processors.extend(RequestProcessors.all())

    @app.get("/")
    @htmy.page(UserList)
    def index() -> list[User] | Response:  # Response in type hint to ensure mypy doesn't complain about it.
        return users

    @app.get("/htmx-or-data")
    @htmy.hx(UserList)
    def htmx_or_data(
        response: Response,
    ) -> list[User] | Response:  # Response in type hint to ensure mypy doesn't complain about it.
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

    @app.get("/hx-no-selector", response_model=None)
    @htmy.hx()  # type: ignore[arg-type]  # HelloWorld is a component, render it as is.
    def hx_no_selector() -> HelloWorld:
        return HelloWorld()

    @app.get("/page-no-selector", response_model=None)
    @htmy.page()  # type: ignore[arg-type]  # HelloWorld is a component, render it as is.
    def page_no_selector() -> HelloWorld:
        return HelloWorld()

    @app.get("/error")
    @app.get("/error/{kind}")
    @htmy.hx(  # type: ignore[arg-type]
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

    @app.get("/error-page")
    @app.get("/error-page/{kind}")
    @htmy.page(  # type: ignore[arg-type]
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

    @app.get("/render-component")
    async def render_component(request: Request) -> HTMLResponse:
        return HTMLResponse(await htmy.render_component(UserListItem(billy), request))

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
        ("/hx-no-selector", {"HX-Request": "true"}, 200, "Hello World!", {}),
        ("/page-no-selector", {"HX-Request": "true"}, 200, "Hello World!", {}),
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
        # Direct component rendering
        ("/render-component", None, 200, "<li >Billy Shears (active=True)</li>", {}),
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
