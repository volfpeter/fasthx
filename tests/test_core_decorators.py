from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from fasthx import hx, page

from .data import DependsRandomNumber, User, user_list_html, user_list_json, users


def render_user_list(result: list[User], *, context: dict[str, Any], request: Request) -> str:
    # Test that the hx() decorator's inserted params are not in context.
    assert len(context) == 1

    # Test that the value of the DependsRandomNumber dependency is in the context.
    random_number = context["random_number"]
    assert random_number == 4

    return "".join(("<ul>", *(f"<li>{u.name} (active={u.active})</li>" for u in result), "</ul>"))


async def async_render_user_list(result: list[User], *, context: dict[str, Any], request: Request) -> str:
    return render_user_list(result, context=context, request=request)


@pytest.fixture
def hx_app() -> FastAPI:
    app = FastAPI()

    @app.get("/")
    @page(render_user_list)
    def index(random_number: DependsRandomNumber) -> list[User]:
        return users

    @app.get("/htmx-or-data")
    @hx(render_user_list)
    def htmx_or_data(random_number: DependsRandomNumber) -> list[User]:
        return users

    @app.get("/htmx-only")  # type: ignore # TODO: figure out why mypy doesn't see the correct type.
    @hx(async_render_user_list, no_data=True)
    async def htmx_only(random_number: DependsRandomNumber) -> list[User]:
        return users

    return app


@pytest.fixture
def hx_client(hx_app: FastAPI) -> TestClient:
    return TestClient(hx_app)


@pytest.mark.parametrize(
    ("route", "headers", "status", "expected"),
    (
        # page() - always renders the HTML result.
        ("/", {"HX-Request": "true"}, 200, user_list_html),
        ("/", None, 200, user_list_html),
        ("/", {"HX-Request": "false"}, 200, user_list_html),
        # hx() - returns JSON for non-HTMX requests.
        ("/htmx-or-data", {"HX-Request": "true"}, 200, user_list_html),
        ("/htmx-or-data", None, 200, user_list_json),
        ("/htmx-or-data", {"HX-Request": "false"}, 200, user_list_json),
        # hy(no_data=True) - raises exception for non-HTMX requests.
        ("/htmx-only", {"HX-Request": "true"}, 200, user_list_html),
        ("/htmx-only", None, 400, ""),
        ("/htmx-only", {"HX-Request": "false"}, 400, ""),
    ),
)
def test_hx_and_page(
    hx_client: TestClient,
    route: str,
    headers: dict[str, str] | None,
    status: int,
    expected: str,
) -> None:
    response = hx_client.get(route, headers=headers)
    assert response.status_code == status
    if status == 400:
        return

    result = response.text
    assert result == expected