from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.testclient import TestClient

from fasthx import Jinja, JinjaContext

from .data import DependsRandomNumber, User, billy, lucy, user_list_html, user_list_json, users


@pytest.fixture
def jinja_app() -> FastAPI:
    app = FastAPI()

    jinja = Jinja(Jinja2Templates("tests/templates"))

    @app.get("/")
    @jinja.page("user-list.html")
    def index() -> list[User]:
        return users

    @app.get("/htmx-or-data")
    @jinja.hx("user-list.html")
    def htmx_or_data() -> dict[str, list[User]]:
        return {"items": users}

    @app.get("/htmx-or-data/<id>")
    @jinja.hx("profile.html")
    def htmx_or_data_by_id(id: int) -> User:
        return billy

    @app.get("/htmx-only")
    @jinja.hx("user-list.html", no_data=True)
    async def htmx_only(random_number: DependsRandomNumber) -> tuple[User, ...]:
        return (billy, lucy)

    return app


@pytest.fixture
def jinja_client(jinja_app: FastAPI) -> TestClient:
    return TestClient(jinja_app)


@pytest.mark.parametrize(
    ("route", "headers", "status", "expected"),
    (
        # jinja.page() - always renders the HTML result.
        ("/", {"HX-Request": "true"}, 200, user_list_html),
        ("/", None, 200, user_list_html),
        ("/", {"HX-Request": "false"}, 200, user_list_html),
        # jinja.hx() - returns JSON for non-HTMX requests.
        ("/htmx-or-data", {"HX-Request": "true"}, 200, user_list_html),
        ("/htmx-or-data", None, 200, f'{{"items":{user_list_json}}}'),
        ("/htmx-or-data", {"HX-Request": "false"}, 200, f'{{"items":{user_list_json}}}'),
        # jinja.hy(no_data=True) - raises exception for non-HTMX requests.
        ("/htmx-only", {"HX-Request": "true"}, 200, user_list_html),
        ("/htmx-only", None, 400, ""),
        ("/htmx-only", {"HX-Request": "false"}, 400, ""),
    ),
)
def test_jinja(
    jinja_client: TestClient,
    route: str,
    headers: dict[str, str] | None,
    status: int,
    expected: str,
) -> None:
    response = jinja_client.get(route, headers=headers)
    assert response.status_code == status
    if status == 400:
        return

    result = response.text
    assert result == expected


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
