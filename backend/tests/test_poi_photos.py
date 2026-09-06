from unittest.mock import Mock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.poi import router
from app.services.poi_photo_service import PoiPhotoService


def row(**changes):
    return {"id": "B123", "name": "翠湖公园", "cityname": "昆明市", "location": "102.7,25.05",
            "photos": [{"url": "https://example.com/park.jpg"}], **changes}


def service(rows):
    instance = PoiPhotoService("test-key")
    instance.request = Mock(return_value=rows)
    return instance


def test_id_verified_and_cached():
    instance = service([row()])
    args = ("翠湖公园", "昆明", "B123", 102.7, 25.05)
    result = instance.resolve(*args)
    assert result["status"] == "available"
    assert result["source"] == "amap"
    assert result["poi_id"] == "B123"
    result["status"] = "tampered"
    assert instance.resolve(*args)["status"] == "available"
    instance.request.assert_called_once_with("/place/detail", {"id": "B123", "extensions": "all"})


@pytest.mark.parametrize("changes", [
    {"id": "B999"}, {"name": "翠湖公园检票处"}, {"cityname": "北京市"},
    {"location": "103.7,25.05"}, {"location": "invalid"},
])
def test_mismatch_never_returns_stock_photo(changes):
    result = service([row(**changes)]).resolve("翠湖公园", "昆明", "B123", 102.7, 25.05)
    assert result["status"] == "unmatched"
    assert result["photo_url"] is None


def test_missing_id_requires_coordinates_and_unique_match():
    instance = service([row()])
    assert instance.resolve("翠湖公园", "昆明")["status"] == "unmatched"
    instance.request.assert_not_called()
    assert instance.resolve("翠湖公园", "昆明", longitude=102.7, latitude=25.05)["status"] == "available"
    assert instance.request.call_args.args[0] == "/place/text"
    ambiguous = service([row(), row(id="B456")])
    assert ambiguous.resolve("翠湖公园", "昆明", longitude=102.7, latitude=25.05)["status"] == "unmatched"


@pytest.mark.parametrize("photos", [[], [{"url": "javascript:alert(1)"}], [{"url": "https://user:pass@example.com/a.jpg"}]])
def test_missing_or_unsafe_photos(photos):
    result = service([row(photos=photos)]).resolve("翠湖公园", "昆明", "B123")
    assert result["status"] == "no_photo"
    assert result["photo_url"] is None


def test_transport_has_short_timeout_no_retry_and_failure_not_cached():
    instance = PoiPhotoService("test-key")
    response = httpx.Response(200, json={"status": "1", "pois": [row()]}, request=httpx.Request("GET", "https://example.com"))
    with patch("app.services.poi_photo_service.httpx.get", side_effect=[httpx.ReadTimeout("secret-url"), response]) as get:
        with pytest.raises(httpx.ReadTimeout):
            instance.resolve("翠湖公园", "昆明", "B123")
        assert get.call_count == 1
        assert instance.resolve("翠湖公园", "昆明", "B123")["status"] == "available"
        assert get.call_args.kwargs["timeout"] == 8


def test_route_returns_safe_unavailable_and_validates_parameters():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    with patch("app.api.routes.poi.get_poi_photo_service") as get:
        get.return_value.resolve.side_effect = RuntimeError("secret-url")
        response = client.get("/poi/photo", params={"name": "翠湖公园", "city": "昆明", "poi_id": "B123"})
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "unavailable"
        assert "secret-url" not in response.text
        assert client.get("/poi/photo", params={"name": "x", "longitude": 999}).status_code == 422
