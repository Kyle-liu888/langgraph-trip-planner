from datetime import date, datetime
from unittest.mock import Mock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.poi import router
from app.services.visit_info_service import CHINA, VisitInfoService, VisitLookupError, official_source, safe_official_url


def place(**changes):
    return {"id": "B000A8UIN8", "name": "故宫博物院", "cityname": "北京市", "location": "116.397,39.918",
            "business": {"opentime_today": "08:30-17:00", "opentime_week": "周二至周日，周一闭馆"}, **changes}


def service(rows=None):
    s = VisitInfoService("mock-key")
    s.request_detail = Mock(return_value=[place()] if rows is None else rows)
    return s


def resolve(s, **kw):
    return s.resolve("故宫博物院", "北京", "B000A8UIN8", 116.397, 39.918, **kw)


def test_future_date_never_uses_today_or_changes_manual_verification():
    s = service()
    now = datetime(2026, 9, 6, 12, tzinfo=CHINA)
    with patch("app.services.visit_info_service.now_china", return_value=now):
        today = resolve(s, visit_date=date(2026, 9, 6))
        future = resolve(s, visit_date=date(2026, 9, 7))
    assert today["opening"]["today_date"] == "2026-09-06"
    assert future["opening"]["today"] is None
    assert future["opening"]["regular"] == "周二至周日，周一闭馆"
    assert future["fetched_at"] == today["fetched_at"]
    assert future["upstream_updated_at"] is None
    assert future["official"]["verified_at"] == "2026-09-06"
    s.request_detail.assert_called_once()


@pytest.mark.parametrize("changes", [{"id": "Bwrong"}, {"name": "故宫博物院检票处"}, {"cityname": "上海市"}, {"location": "117.397,39.918"}])
def test_wrong_identity_has_no_hours_or_verified_links(changes):
    r = resolve(service([place(**changes)]))
    assert r["match_status"] == "unmatched"
    assert r["opening"]["today"] is None
    assert r["official"] is None


@pytest.mark.parametrize("business", [None, [], {}, {"cost": "60", "opentime_today": []}])
def test_absent_hours_never_use_cost_as_price(business):
    r = resolve(service([place(business=business)]))
    assert r["status"] == "no_data"
    assert "cost" not in r and "ticket_price" not in r
    assert r["official"]


def test_today_only_is_not_applicable_to_future():
    s = service([place(business={"opentime_today": "08:00-18:00"})])
    r = resolve(s, visit_date=date(2099, 1, 1))
    assert r["status"] == "no_data" and r["opening"]["today"] is None


@pytest.mark.parametrize("error,status", [(VisitLookupError("permission_denied"), "permission_denied"), (httpx.ReadTimeout("private-url"), "timeout"), (RuntimeError("private-url"), "unavailable")])
def test_upstream_failure_retains_official_entry(error, status):
    s = service()
    s.request_detail.side_effect = error
    r = resolve(s)
    assert r["status"] == status and r["official"]
    assert "private-url" not in str(r)
    resolve(s)
    assert s.request_detail.call_count == 2


def test_cache_ttl_midnight_and_capacity():
    s = service()
    with patch("app.services.visit_info_service.now_china", return_value=datetime(2026, 9, 6, 23, 59, tzinfo=CHINA)):
        resolve(s)
        resolve(s)
    with patch("app.services.visit_info_service.now_china", return_value=datetime(2026, 9, 7, 0, 1, tzinfo=CHINA)):
        resolve(s)
    assert s.request_detail.call_count == 2
    with s.lock:
        for key in s.cache:
            s.cache[key] = (0, s.cache[key][1])
    resolve(s)
    assert s.request_detail.call_count == 3
    s.lookup = Mock(return_value={"status": "no_data", "poi_id": "Btest"})
    for i in range(514):
        s.resolve(str(i), "北京", "Btest")
    assert len(s.cache) == 512


def test_legacy_no_id_requires_unique_coordinate_match():
    s = service()
    photos = Mock()
    photos.request.return_value = [place()]
    with patch("app.services.visit_info_service.get_poi_photo_service", return_value=photos):
        assert s.resolve("故宫博物院", "北京")["status"] == "unmatched"
        photos.request.assert_not_called()
        assert s.resolve("故宫博物院", "北京", longitude=116.397, latitude=39.918)["status"] == "available"
    s.request_detail.assert_called_once_with("B000A8UIN8")


def test_raw_http_permission_and_deadline_no_retry():
    s = VisitInfoService("mock-key")
    response = httpx.Response(200, json={"status": "0", "infocode": "10005"}, request=httpx.Request("GET", "https://example.com"))
    with patch("app.services.visit_info_service.httpx.get", return_value=response) as get:
        assert resolve(s)["status"] == "permission_denied"
        assert get.call_count == 1
        assert get.call_args.kwargs["timeout"] == 8
        assert get.call_args.kwargs["params"]["show_fields"] == "business"


def test_registry_rejects_wrong_id_city_and_unsafe_urls():
    assert official_source("颐和园", "北京", "B000A7O1CU")
    assert official_source("天坛公园", "北京", "B000A81CB2")
    assert official_source("故宫博物院", "沈阳", "") is None
    assert official_source("故宫博物院", "北京", "Bwrong") is None
    assert not safe_official_url("javascript:alert(1)")
    assert not safe_official_url("https://www.dpm.org.cn.evil.example/")
    assert not safe_official_url("https://user@www.dpm.org.cn/")


def test_route_input_validation_and_logged_in_wiring():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    assert client.get("/poi/visit-info?name=test&city=北京&longitude=1").status_code == 422
    assert client.get("/poi/visit-info?name=test&city=北京&visit_date=invalid").status_code == 422
    with patch("app.api.routes.poi.get_visit_info_service", return_value=service()):
        assert client.get("/poi/visit-info", params={"name": "故宫博物院", "city": "北京", "poi_id": "B000A8UIN8"}) .json()["data"]["status"] == "available"
    from app.api.main import app as main
    assert TestClient(main).get("/api/poi/visit-info?name=test&city=北京").status_code == 401
