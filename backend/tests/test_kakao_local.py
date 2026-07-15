import asyncio

from app.core.config import Settings
from app.services import kakao_local


def test_kakao_address_search_and_reverse_mapping(monkeypatch) -> None:
    async def fake_get(_settings, path, _params):
        if "search/address" in path:
            return {
                "documents": [
                    {
                        "address_name": "서울 중구 태평로1가 31",
                        "x": "126.978652",
                        "y": "37.566826",
                        "address": {"address_name": "서울 중구 태평로1가 31"},
                        "road_address": {
                            "address_name": "서울 중구 세종대로 110",
                            "building_name": "서울특별시청",
                            "zone_no": "04524",
                        },
                    }
                ]
            }
        return {
            "documents": [
                {
                    "address": {"address_name": "서울 중구 태평로1가 31"},
                    "road_address": {"address_name": "서울 중구 세종대로 110", "zone_no": "04524"},
                }
            ]
        }

    monkeypatch.setattr(kakao_local, "_get", fake_get)
    settings = Settings(_env_file=None, kakao_rest_api_key="test-key")
    searched = asyncio.run(kakao_local.search_address(settings, "서울시청"))
    reversed_address = asyncio.run(kakao_local.reverse_geocode(settings, 37.566826, 126.978652))

    assert searched[0]["address"] == "서울 중구 세종대로 110"
    assert searched[0]["zipcode"] == "04524"
    assert searched[0]["latitude"] == 37.566826
    assert reversed_address == {
        "address": "서울 중구 세종대로 110",
        "road_address": "서울 중구 세종대로 110",
        "lot_address": "서울 중구 태평로1가 31",
        "zipcode": "04524",
    }
