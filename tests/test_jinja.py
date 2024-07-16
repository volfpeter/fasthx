from typing import Any

import pytest
from fastapi import FastAPI, Response
from fastapi.templating import Jinja2Templates
from fastapi.testclient import TestClient

from fasthx import Jinja, JinjaContext, TemplateHeader

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


@pytest.fixture
def jinja_app() -> FastAPI:
    app = FastAPI()

    jinja = Jinja(Jinja2Templates("tests/templates"))

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
