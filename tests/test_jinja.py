import pytest
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.testclient import TestClient

from fasthx import Jinja

from .data import DependsRandomNumber, User, html_user_list, json_user_list, users


@pytest.fixture
def jinja_app() -> FastAPI:
    app = FastAPI()

    jinja = Jinja(Jinja2Templates("tests/templates"))

    @app.get("/htmx-or-data")
    @jinja("user-list.html")
    def htmx_or_data() -> dict[str, list[User]]:
        return {"users": users}

    @app.get("/htmx-only")
    @jinja("user-list.html", no_data=True)
    async def htmx_only(random_number: DependsRandomNumber) -> dict[str, list[User]]:
        return {"users": users}

    return app


@pytest.fixture
def jinja_client(jinja_app: FastAPI) -> TestClient:
    return TestClient(jinja_app)


@pytest.mark.parametrize(
    ("route", "headers", "status", "expected"),
    (
        ("/htmx-or-data", {"HX-Request": "true"}, 200, html_user_list),
        ("/htmx-or-data", None, 200, f'{{"users":{json_user_list}}}'),
        ("/htmx-or-data", {"HX-Request": "false"}, 200, f'{{"users":{json_user_list}}}'),
        ("/htmx-only", {"HX-Request": "true"}, 200, html_user_list),
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
