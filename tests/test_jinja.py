from typing import Any

import pytest
from fastapi import FastAPI, Response
from fastapi.templating import Jinja2Templates
from fastapi.testclient import TestClient

from fasthx import Jinja, JinjaContext, JinjaPath, TemplateHeader

from .data import (
    DependsRandomNumber,
    User,
    billy,
    billy_html_header,
    billy_html_paragraph,
    billy_html_span,
    billy_json,
    lucy,
    user_list_html,
    user_list_json,
    users,
)


class RenderedError(Exception):
    def __init__(self, data: dict[str, Any], *, response: Response) -> None:
        super().__init__("Data validation failed.")

        # Pattern for setting the response status code for error rendering responses.
        response.status_code = 456

        # Pattern to make the data available in Jinja rendering contexts. Not used in tests.
        for key, value in data.items():
            setattr(self, key, value)


@pytest.fixture
def jinja_app() -> FastAPI:
    app = FastAPI()

    jinja = Jinja(Jinja2Templates("tests/templates"))
    no_data_jinja = Jinja(Jinja2Templates("tests/templates"), no_data=True)

    @app.get("/")
    @jinja.page("user-list.jinja")
    def index() -> list[User]:
        return users

    @app.get("/htmx-or-data")
    @jinja.hx("user-list.jinja")
    def htmx_or_data(response: Response) -> dict[str, list[User]]:
        response.headers["test-header"] = "exists"
        return {"items": users}

    @app.get("/htmx-only")
    @jinja.hx("user-list.jinja", no_data=True)
    async def htmx_only(random_number: DependsRandomNumber) -> tuple[User, ...]:
        return (billy, lucy)

    @app.get("/htmx-or-data/{id}")
    @jinja.hx(
        TemplateHeader(
            "X-Component",
            {
                "header": "h1.jinja",
                "paragraph": "p.jinja",
                "hello-world": JinjaPath("hello-world.jinja"),
            },
            default="span.jinja",
        ),
        prefix="profile",
    )
    def htmx_or_data_by_id(id: int) -> User:
        return billy

    @app.get("/header-with-no-default")
    @jinja.hx(
        TemplateHeader(
            "X-Component",
            {
                "header": "profile/h1.jinja",
                "paragraph": "profile/p.jinja",
                "span": "profile/span.jinja",
            },
        ),
    )
    def header_with_no_default() -> User:
        return billy

    @app.get("/error")
    @jinja.hx(
        TemplateHeader("X-Component", {}),  # No rendering if there's no exception.
        error_template=TemplateHeader(
            "X-Error-Component",
            {},
            default="hello-world.jinja",
            error=RenderedError,
        ),
        no_data=True,
    )
    def error(response: Response) -> None:
        raise RenderedError({"a": 1, "b": 2}, response=response)

    @app.get("/error-page")
    @jinja.page(
        TemplateHeader("X-Component", {}),  # No rendering if there's no exception.
        error_template=TemplateHeader(
            "X-Error-Component",
            {},
            default="hello-world.jinja",
            error=(RenderedError, TypeError, ValueError),  # Test error tuple
        ),
    )
    def error_page(response: Response) -> None:
        raise RenderedError({"a": 1, "b": 2}, response=response)

    @app.get("/global-no-data")
    @no_data_jinja.hx("user-list.jinja", no_data=False)
    def global_no_data() -> list[User]:
        return []

    return app


@pytest.fixture
def jinja_client(jinja_app: FastAPI) -> TestClient:
    # raise_server_exception must be disabled. Without it, unhandled server
    # errors would result in an exception instead of a HTTP 500 response.
    return TestClient(jinja_app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    ("route", "headers", "status", "expected", "response_headers"),
    (
        # jinja.page() - always renders the HTML result.
        ("/", {"HX-Request": "true"}, 200, user_list_html, {}),
        ("/", None, 200, user_list_html, {}),
        ("/", {"HX-Request": "false"}, 200, user_list_html, {}),
        # jinja.hx() - returns JSON for non-HTMX requests.
        ("/htmx-or-data", {"HX-Request": "true"}, 200, user_list_html, {"test-header": "exists"}),
        ("/htmx-or-data", None, 200, f'{{"items":{user_list_json}}}', {"test-header": "exists"}),
        (
            "/htmx-or-data",
            {"HX-Request": "false"},
            200,
            f'{{"items":{user_list_json}}}',
            {"test-header": "exists"},
        ),
        ("/htmx-or-data/1", None, 200, billy_json, {}),
        ("/htmx-or-data/2", {"HX-Request": "true"}, 200, billy_html_span, {}),
        ("/htmx-or-data/3", {"HX-Request": "true", "X-Component": "header"}, 200, billy_html_header, {}),
        # JinjaPath test (decorator prefix not used).
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
        # jinja.hx(no_data=True) - raises exception for non-HTMX requests.
        ("/htmx-only", {"HX-Request": "true"}, 200, user_list_html, {}),
        ("/htmx-only", None, 400, "", {}),
        ("/htmx-only", {"HX-Request": "false"}, 400, "", {}),
        # hx() error rendering
        ("/error", {"HX-Request": "true"}, 456, "Hello World!", {}),
        # page() error rendering
        ("/error-page", None, 456, "Hello World!", {}),
        # Globally disabled data responses
        ("/global-no-data", None, 400, "", {}),
    ),
)
def test_jinja(
    jinja_client: TestClient,
    route: str,
    headers: dict[str, str] | None,
    status: int,
    expected: str,
    response_headers: dict[str, str],
) -> None:
    response = jinja_client.get(route, headers=headers)
    assert response.status_code == status
    if status >= 400:
        return

    result = response.text
    assert result == expected

    assert all((response.headers.get(key) == value) for key, value in response_headers.items())


class TestJinjaContext:
    @pytest.mark.parametrize(
        ("route_result", "route_converted"),
        (
            (billy, billy.model_dump()),
            (lucy, lucy.model_dump()),
            ((billy, lucy), {"items": (billy, lucy)}),
            ([billy, lucy], {"items": [billy, lucy]}),
            ({billy, lucy}, {"items": {billy, lucy}}),
            ({"billy": billy, "lucy": lucy}, {"billy": billy, "lucy": lucy}),
        ),
    )
    def test_unpack_methods(self, route_result: Any, route_converted: dict[str, Any]) -> None:
        route_context = {"extra": "added"}

        result = JinjaContext.unpack_result(route_result=route_result, route_context=route_context)
        assert result == route_converted

        result = JinjaContext.unpack_result_with_route_context(
            route_result=route_result, route_context=route_context
        )
        assert result == {**route_context, **route_converted}

    def test_unpack_result_with_route_context_conflict(self) -> None:
        with pytest.raises(ValueError):
            JinjaContext.unpack_result_with_route_context(
                route_result=billy, route_context={"name": "Not Billy"}
            )

    def test_use_converters(self) -> None:
        context_factory = JinjaContext.use_converters(
            lambda _: {"route_result": 1},
            lambda _: {"route_context": 2},
        )
        assert context_factory(route_result=None, route_context={}) == {
            "route_result": 1,
            "route_context": 2,
        }

    def test_use_converters_name_conflict(self) -> None:
        context_factory = JinjaContext.use_converters(
            lambda _: {"x": 1},
            lambda _: {"x": 2},
        )
        with pytest.raises(ValueError):
            context_factory(route_result=None, route_context={})

    def test_wrap_as(self) -> None:
        result_only = JinjaContext.wrap_as("item")
        assert result_only is JinjaContext.wrap_as("item")

        result_and_context = JinjaContext.wrap_as("item", "route")
        route_result, route_context = 22, {"4": 4}

        assert {"item": route_result} == result_only(route_result=route_result, route_context=route_context)
        assert {"item": route_result, "route": route_context} == result_and_context(
            route_result=route_result, route_context=route_context
        )

    def test_wrap_as_name_conflict(self) -> None:
        with pytest.raises(ValueError):
            JinjaContext.wrap_as("foo", "foo")
