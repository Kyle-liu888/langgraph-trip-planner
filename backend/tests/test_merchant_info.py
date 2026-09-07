"""All merchant data is mocked: no model/map quota or external requests."""
from unittest.mock import Mock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.poi import router
from app.models.merchant_info import MerchantInfo
from app.services.merchant_info_service import (
    MerchantInfoService, MerchantLookupError, is_generic_merchant,
    merchant_registry, registered_links, safe_platform_url,
)


def place(**changes):
    return {"id": "B123", "name": "示例餐厅(前门店)", "cityname": "北京市", "typecode": "050100",
            "address": "东城区前门大街30号", "location": "116.397,39.918",
            "business": {"rating": "4.8", "tag": "烤鸭,四合院;家常菜", "cost": "168"},
            "photos": [{"url": "https://photos.example.com/a.jpg", "title": "庭院"}], **changes}


@pytest.fixture(autouse=True)
def empty_registry():
    with patch("app.services.merchant_info_service.merchant_registry", return_value=[]):
        yield


def service(rows=None, details=None):
    s = MerchantInfoService("mock-key")
    s.request = Mock(side_effect=[rows if rows is not None else [place()], details if details is not None else [place()]])
    return s


def resolve(s, **overrides):
    args = {"kind": "food", "name": "示例餐厅(前门店)", "city": "北京", "poi_id": "B123"}
    args.update(overrides)
    return s.resolve(**args)


def registration(**changes):
    return {"kind": "food", "name": "示例餐厅(前门店)", "city": "北京", "address": "东城区前门大街30号",
            "poi_ids": ["B123"], "location": {"longitude": 116.397, "latitude": 39.918},
            "links": [{"platform": "dianping", "url": "https://www.dianping.com/shop/123", "verified_at": "2026-09-07"}], **changes}


def test_verified_data_contract_and_no_price_or_review_fields():
    result = resolve(service())
    MerchantInfo.model_validate(result)
    assert result["match_status"] == "matched" and result["data_status"] == "available"
    assert result["place"]["address"] == "东城区前门大街30号"
    assert result["rating"] == "4.8" and result["food_tags"] == ["烤鸭", "四合院", "家常菜"]
    assert result["photos"] == [{"url": "https://photos.example.com/a.jpg", "title": "庭院"}]
    assert "poiid=B123" in result["source"]["url"]
    assert result["source"]["queried_at"] == result["queried_at"]
    assert "高德" in result["source"]["name"]
    assert not {"cost", "price", "room_price", "reviews", "updated_at"} & result.keys()


@pytest.mark.parametrize("changes", [
    {"id": "B456"}, {"name": "示例餐厅(王府井店)"}, {"name": "示例餐厅"},
    {"cityname": "上海市"}, {"typecode": "100100"}, {"typecode": ""},
    {"address": "东城区前门大街31号"}, {"location": "117.397,39.918"}, {"location": "nan,39.918"},
])
def test_identity_conflict_never_exposes_another_branch(changes):
    s = service([place(**changes)])
    with patch("app.services.merchant_info_service.merchant_registry", return_value=[registration()]):
        result = resolve(s, address="东城区前门大街30号", longitude=116.397, latitude=39.918)
    assert result["match_status"] == "unmatched"
    assert result["place"] is None and not result["photos"] and not result["rating"]
    assert result["source"] is None and result["links"] == []
    s.request.assert_called_once()


def test_branch_parentheses_and_city_prefix_normalize_without_deleting_branch():
    result = resolve(service(), name="示例餐厅（前门店）", city="北京市", address="北京市东城区前门大街30号")
    assert result["match_status"] == "matched"


def test_v5_conflict_clears_basic_identity_and_registered_links():
    with patch("app.services.merchant_info_service.merchant_registry", return_value=[registration()]):
        result = resolve(service(details=[place(name="示例餐厅(另一分店)")]))
    assert result["match_status"] == "unmatched"
    assert result["place"] is None and result["source"] is None and not result["links"]


def test_legacy_unique_coordinates_or_specific_exact_address_required():
    s = service()
    assert resolve(s, poi_id="")["match_status"] == "insufficient"
    assert resolve(s, poi_id="", address="前门大街")["match_status"] == "insufficient"
    s.request.assert_not_called()
    result = resolve(s, poi_id="", address="东城区前门大街30号")
    assert result["match_status"] == "matched"
    assert s.request.call_args_list[0].args[1] == "text"
    assert s.request.call_args_list[0].args[2]["types"] == "050000"
    result = resolve(service(), poi_id="", longitude=116.397, latitude=39.918)
    assert result["match_status"] == "matched"


def test_search_cannot_take_first_of_multiple_matching_pois():
    s = service([place(), place(id="B456")])
    result = resolve(s, poi_id="", address="东城区前门大街30号")
    assert result["match_status"] == "ambiguous" and result["source"] is None
    s.request.assert_called_once()


def test_search_deduplicates_same_id_but_never_uses_unrelated_first_hit():
    s = service([place(name="示例餐厅(王府井店)", id="B456"), place(), place()])
    result = resolve(s, poi_id="", longitude=116.397, latitude=39.918)
    assert result["place"]["poi_id"] == "B123"


@pytest.mark.parametrize("name", ["酒店早餐", "酒店自助早餐", "民宿早餐", "客栈早餐", "住宿早餐", "当地小吃", "北京本地菜午餐", "北京市当地小吃", "第1天午餐", "北京第三天晚餐"])
def test_generic_meals_do_not_query_or_link(name):
    s = service()
    result = resolve(s, name=name)
    assert result["match_status"] == "generic" and not result["links"]
    s.request.assert_not_called()
    assert is_generic_merchant("food", name, "北京")
    assert not is_generic_merchant("food", "酒店早餐餐厅(前门店)", "北京")


@pytest.mark.parametrize("name", ["舒适型酒店", "北京当地酒店", "北京市民宿"])
def test_generic_hotel_never_forces_lookup(name):
    s = service()
    assert resolve(s, kind="hotel", name=name)["match_status"] == "generic"
    s.request.assert_not_called()


@pytest.mark.parametrize("business", [None, [], {}, {"rating": [], "cost": "188"}, {"rating": "暂无"}, {"rating": "nan"}, {"rating": "0"}, {"rating": "9.9"}])
def test_optional_fields_missing_never_invents_rating_or_reuses_cost(business):
    result = resolve(service(details=[place(business=business, photos=[])]))
    assert result["match_status"] == "matched" and result["data_status"] == "no_data"
    assert result["rating"] is None and result["food_tags"] == [] and not result["photos"]


def test_hotel_uses_only_sourced_rating_and_does_not_treat_food_tag_as_hotel_features():
    row = place(name="示例酒店(前门店)", typecode="100100")
    result = resolve(service([row], [row]), kind="hotel", name=row["name"])
    assert result["rating"] == "4.8" and not result["food_tags"]


def test_photo_safety_dedupe_limit_and_raw_titles():
    photos = [{"url": "javascript:alert(1)"}, {"url": "https://user:secret@a.example/a.jpg"}, {"url": "https://a.example:999/a.jpg"},
              {"url": "https://a.example/1.jpg", "title": []}, {"url": "https://a.example/1.jpg"},
              {"url": "https://a.example/2.jpg", "title": "实拍原始标题"}, {"url": "https://a.example/3.jpg"}, {"url": "https://a.example/4.jpg"}]
    result = resolve(service(details=[place(photos=photos)]))
    assert len(result["photos"]) == 3
    assert result["photos"][0]["title"] == "门店参考图"
    assert result["photos"][1]["title"] == "实拍原始标题"
    assert "4.jpg" not in str(result["photos"])


def test_food_tags_are_unique_and_bounded():
    result = resolve(service(details=[place(business={"tag": "烧鸭,烧鸭;" + ",".join(str(i) for i in range(20))})]))
    assert len(result["food_tags"]) == 8 and result["food_tags"].count("烧鸭") == 1


@pytest.mark.parametrize("error,status", [(MerchantLookupError("permission_denied"), "permission_denied"),
    (httpx.ReadTimeout("secret-key-private-url"), "timeout"), (RuntimeError("secret-key-private-url"), "unavailable")])
@pytest.mark.parametrize("basic_matched", [True, False])
def test_upstream_failures_preserve_independent_registry_links_and_never_cache_or_leak(error, status, basic_matched):
    s = MerchantInfoService("mock-key")
    s.request = Mock(side_effect=[[place()], error] if basic_matched else error)
    with patch("app.services.merchant_info_service.merchant_registry", return_value=[registration()]), \
         patch("app.services.merchant_info_service.logger") as log:
        result = resolve(s)
    assert result["data_status"] == status and len(result["links"]) == 1
    assert bool(result["source"]) == basic_matched
    assert result["links"][0]["verified_at"] == "2026-09-07"
    assert "secret-key-private-url" not in str(result) + str(log.mock_calls)
    assert not s.cache


def test_registry_requires_branch_evidence_and_rejects_conflicts_and_ambiguity():
    args = {"kind": "food", "name": "示例餐厅(前门店)", "city": "北京", "address": "", "poi_id": "", "longitude": None, "latitude": None}
    with patch("app.services.merchant_info_service.merchant_registry", return_value=[registration()]):
        assert not registered_links(**args)
        assert registered_links(**{**args, "poi_id": "B123"})
        assert registered_links(**{**args, "address": "北京市东城区前门大街30号"})
        assert registered_links(**{**args, "longitude": 116.397, "latitude": 39.918})
        assert not registered_links(**{**args, "poi_id": "Bwrong", "address": "东城区前门大街30号"})
        assert not registered_links(**{**args, "poi_id": "B123", "address": "东城区前门大街31号"})
        assert not registered_links(**{**args, "poi_id": "B123", "longitude": 117.397, "latitude": 39.918})
        assert not registered_links(**{**args, "poi_id": "B123", "city": "上海"})
    with patch("app.services.merchant_info_service.merchant_registry", return_value=[registration(), registration()]):
        assert not registered_links(**{**args, "poi_id": "B123"})


@pytest.mark.parametrize("url", ["javascript:alert(1)", "https://www.dianping.com.evil.test/shop/1", "https://www.dianping.com/", "https://m.dianping.com/dphome", "https://www.dianping.com/pclogin", "https://www.dianping.com/search/keyword/beijing", "https://user@www.dianping.com/shop/1", "https://www.dianping.com/shop/1?token=secret", "https://www.dianping.com/shop/1?sessionId=secret"])
def test_registry_url_rejects_unsafe_or_nonmerchant_pages(url):
    assert not safe_platform_url("dianping", url)


def test_registry_loader_validates_dates_domains_and_kind_without_network():
    merchant_registry.cache_clear()
    with patch("app.services.merchant_info_service.SOURCE_FILE") as source:
        import json
        source.read_text.return_value = json.dumps({"items": [registration()]})
        assert merchant_registry()[0]["links"][0]["platform"] == "dianping"
        merchant_registry.cache_clear()
        invalid = registration()
        invalid["links"][0]["verified_at"] = "bad-date"
        source.read_text.return_value = json.dumps({"items": [invalid]})
        with pytest.raises(ValueError):
            merchant_registry()
    merchant_registry.cache_clear()
    assert safe_platform_url("ctrip", "https://m.ctrip.com/html5/hotel/hoteldetail/99831822.html")


def test_cache_is_defensive_bounded_and_expires_without_changing_manual_dates():
    s = MerchantInfoService("mock-key")
    s.request = Mock(return_value=[place()])
    with patch("app.services.merchant_info_service.merchant_registry", return_value=[registration()]):
        first = resolve(s)
        first["photos"].clear()
        second = resolve(s)
        assert second["photos"] and first["queried_at"] == second["queried_at"]
        assert s.request.call_count == 2
        assert second["links"][0]["verified_at"] == "2026-09-07"
        for key in s.cache:
            s.cache[key] = (0, s.cache[key][1])
        resolve(s)
        assert s.request.call_count == 4
    for i in range(514):
        resolve(s, name=str(i), poi_id="")
    assert len(s.cache) == 512


def test_raw_http_deadline_shared_limiter_no_retry_and_permission_status():
    s = MerchantInfoService("not-printed")
    request = httpx.Request("GET", "https://example.com")
    responses = [httpx.Response(200, json={"status": "1", "pois": [place()]}, request=request),
                 httpx.Response(200, json={"status": "0", "infocode": "10005"}, request=request)]
    with patch("app.services.merchant_info_service.httpx.get", side_effect=responses) as get, \
         patch("app.services.merchant_info_service.AmapPlannerClient._wait_for_amap_slot") as slot:
        result = resolve(s)
    assert result["data_status"] == "permission_denied" and result["place"]
    assert get.call_count == slot.call_count == 2
    assert all(call.kwargs["timeout"] == 8 for call in get.call_args_list)
    assert get.call_args.kwargs["params"]["show_fields"] == "business,photos"


def test_missing_key_never_makes_network_request():
    with patch("app.services.merchant_info_service.httpx.get") as get:
        result = resolve(MerchantInfoService(""))
    assert result["data_status"] == "permission_denied"
    get.assert_not_called()


@pytest.mark.parametrize("location", [{"longitude": 1}, {"longitude": float("nan"), "latitude": 1}, {"longitude": 181, "latitude": 1}])
def test_internal_invalid_coordinates_are_rejected(location):
    with pytest.raises(ValueError):
        resolve(service(), **location)


def test_route_validation_response_filtering_and_login_protection():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    base = {"kind": "food", "name": "示例餐厅(前门店)", "city": "北京", "poi_id": "B123"}
    for changes in [{"kind": "scenic"}, {"longitude": 1}, {"longitude": 181, "latitude": 1}, {"longitude": "nan", "latitude": 1}, {"poi_id": "B?key=bad"}]:
        assert client.get("/poi/merchant-info", params={**base, **changes}).status_code == 422
    with patch("app.api.routes.poi.get_merchant_info_service", return_value=service()):
        response = client.get("/poi/merchant-info", params=base)
    assert response.status_code == 200
    MerchantInfo.model_validate(response.json()["data"])
    from app.api.main import app as main
    assert TestClient(main).get("/api/poi/merchant-info", params=base).status_code == 401
