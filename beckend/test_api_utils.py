from src.api.utils import success_response, raise_http_error
from src.api.schemas import APIResponse
import pytest


def test_success_response_wraps_payload():
    payload = {"hello": "world"}
    response = success_response(data=payload, message="ok")
    assert isinstance(response, APIResponse)
    assert response.success is True
    assert response.data == payload
    assert response.message == "ok"


def test_raise_http_error_builds_payload():
    with pytest.raises(Exception) as excinfo:
        raise_http_error(400, error="bad_request", message="Invalid")

    detail = excinfo.value.detail  # type: ignore[attr-defined]
    assert detail["error"] == "bad_request"
    assert detail["message"] == "Invalid"
