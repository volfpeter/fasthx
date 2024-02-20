import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient

from fasthx import DependsHXRequest, get_hx_request


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()

    @app.get("/")
    def main(
        hx_request_1: DependsHXRequest,
        hx_request_2: Request | None = Depends(get_hx_request),  # noqa: B008
    ) -> dict[str, bool]:
        return {
            "hx_request_1": hx_request_1 is not None,
            "hx_request_2": hx_request_2 is not None,
        }

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.mark.parametrize(
    ("headers", "is_hx_request"),
    (
        (None, False),
        ({"HX-Request": "false"}, False),
        ({"HX-Request": "true"}, True),
    ),
)
def test_get_hx_request(client: TestClient, headers: dict[str, str] | None, is_hx_request: bool) -> None:
    response = client.get("/", headers=headers)
    result = response.json()
    assert result["hx_request_1"] == result["hx_request_2"] == is_hx_request
