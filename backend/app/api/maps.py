from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import Settings, get_settings
from app.schemas.map import AddressSearchResult, ReverseGeocodeResult
from app.services.kakao_local import KakaoLocalError, reverse_geocode, search_address


router = APIRouter(prefix="/maps", tags=["maps"])


@router.get("/address-search", response_model=list[AddressSearchResult])
async def address_search(
    q: str = Query(min_length=2, max_length=200),
    settings: Settings = Depends(get_settings),
) -> list[dict[str, object]]:
    try:
        return await search_address(settings, q.strip())
    except KakaoLocalError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/reverse-geocode", response_model=ReverseGeocodeResult)
async def coordinates_to_address(
    latitude: float = Query(ge=33.0, le=39.5),
    longitude: float = Query(ge=124.0, le=132.0),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    try:
        result = await reverse_geocode(settings, latitude, longitude)
    except KakaoLocalError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="해당 좌표의 주소를 찾을 수 없습니다.")
    return result

