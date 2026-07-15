from pydantic import BaseModel


class AddressSearchResult(BaseModel):
    address: str
    road_address: str
    lot_address: str
    detail_hint: str
    zipcode: str
    longitude: float
    latitude: float


class ReverseGeocodeResult(BaseModel):
    address: str
    road_address: str
    lot_address: str
    zipcode: str

