from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings


class KakaoLocalError(RuntimeError):
    pass


def _headers(settings: Settings) -> dict[str, str]:
    key = settings.kakao_rest_api_key.strip()
    if not key:
        raise KakaoLocalError("카카오 REST API 키가 설정되지 않았습니다.")
    return {"Authorization": f"KakaoAK {key}"}


async def _get(settings: Settings, path: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(base_url="https://dapi.kakao.com", timeout=7.0) as client:
            response = await client.get(path, params=params, headers=_headers(settings))
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise KakaoLocalError("카카오 위치 정보를 불러오지 못했습니다.") from exc
    if not isinstance(payload, dict):
        raise KakaoLocalError("카카오 위치 응답 형식이 올바르지 않습니다.")
    return payload


async def search_address(settings: Settings, query: str) -> list[dict[str, object]]:
    payload = await _get(
        settings,
        "/v2/local/search/address.json",
        {"query": query, "analyze_type": "similar", "size": 10},
    )
    results: list[dict[str, object]] = []
    for document in payload.get("documents", []):
        if not isinstance(document, dict):
            continue
        road = document.get("road_address") or {}
        lot = document.get("address") or {}
        road_name = str(road.get("address_name") or "")
        lot_name = str(lot.get("address_name") or "")
        address = road_name or str(document.get("address_name") or "") or lot_name
        try:
            longitude = float(document["x"])
            latitude = float(document["y"])
        except (KeyError, TypeError, ValueError):
            continue
        results.append(
            {
                "address": address,
                "road_address": road_name,
                "lot_address": lot_name,
                "detail_hint": str(road.get("building_name") or ""),
                "zipcode": str(road.get("zone_no") or ""),
                "longitude": longitude,
                "latitude": latitude,
            }
        )
    return results


async def reverse_geocode(settings: Settings, latitude: float, longitude: float) -> dict[str, str] | None:
    payload = await _get(
        settings,
        "/v2/local/geo/coord2address.json",
        {"x": longitude, "y": latitude, "input_coord": "WGS84"},
    )
    documents = payload.get("documents", [])
    if not documents:
        return None
    document = documents[0]
    road = document.get("road_address") or {}
    lot = document.get("address") or {}
    road_name = str(road.get("address_name") or "")
    lot_name = str(lot.get("address_name") or "")
    return {
        "address": road_name or lot_name,
        "road_address": road_name,
        "lot_address": lot_name,
        "zipcode": str(road.get("zone_no") or ""),
    }

