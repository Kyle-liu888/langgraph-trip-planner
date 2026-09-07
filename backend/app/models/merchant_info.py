"""Read-only merchant card DTOs, deliberately separate from persisted TripPlan."""
from typing import Literal

from pydantic import BaseModel


MerchantKind = Literal["food", "hotel"]


class MerchantLocation(BaseModel):
    longitude: float
    latitude: float


class MerchantPlace(BaseModel):
    poi_id: str
    name: str
    address: str
    city: str
    location: MerchantLocation | None = None


class MerchantPhoto(BaseModel):
    url: str
    title: str


class MerchantSource(BaseModel):
    name: str
    url: str
    queried_at: str


class MerchantLink(BaseModel):
    platform: Literal["dianping", "meituan", "ctrip"]
    label: str
    url: str
    verified_at: str


class MerchantInfo(BaseModel):
    match_status: Literal["matched", "unmatched", "ambiguous", "insufficient", "generic"]
    data_status: Literal["available", "no_data", "permission_denied", "timeout", "unavailable"]
    message: str
    place: MerchantPlace | None = None
    photos: list[MerchantPhoto]
    rating: str | None = None
    food_tags: list[str]
    source: MerchantSource | None = None
    links: list[MerchantLink]
    queried_at: str


class MerchantInfoResponse(BaseModel):
    success: bool = True
    data: MerchantInfo
