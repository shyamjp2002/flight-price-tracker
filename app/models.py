from datetime import date

from pydantic import BaseModel, Field, field_validator


class WatchCreate(BaseModel):
    origin: str = Field(min_length=3, max_length=3, description="IATA code, e.g. HYD")
    destination: str = Field(min_length=3, max_length=3, description="IATA code, e.g. DXB")
    depart_date: date
    return_date: date | None = None
    adults: int = Field(default=1, ge=1, le=9)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    target_price: float | None = Field(default=None, gt=0)
    flex_days: int = Field(
        default=0,
        ge=0,
        le=7,
        description="also check this many days either side of the dates",
    )

    @field_validator("origin", "destination", "currency")
    @classmethod
    def upper(cls, value: str) -> str:
        return value.upper()

    @field_validator("depart_date")
    @classmethod
    def depart_not_past(cls, value: date) -> date:
        if value < date.today():
            raise ValueError("depart_date is in the past")
        return value

    @field_validator("return_date")
    @classmethod
    def return_after_depart(cls, value: date | None, info) -> date | None:
        depart = info.data.get("depart_date")
        if value and depart and value < depart:
            raise ValueError("return_date must not be before depart_date")
        return value


class PricePoint(BaseModel):
    price: float
    currency: str
    carrier: str | None = None
    deep_link: str | None = None
    for_date: date | None = None
    checked_at: str


class Recommendation(BaseModel):
    verdict: str
    reason: str
    latest_price: float | None = None
    lowest_price: float | None = None
    average_price: float | None = None
    percent_vs_average: float | None = None
    trend: str = "flat"
    days_to_departure: int | None = None


class Watch(BaseModel):
    id: int
    origin: str
    destination: str
    depart_date: date
    return_date: date | None
    adults: int
    currency: str
    target_price: float | None
    flex_days: int = 0
    active: bool
    created_at: str
    latest_price: float | None = None
    lowest_price: float | None = None
    checks: int = 0
    origin_label: str = ""
    destination_label: str = ""
    recommendation: Recommendation | None = None


class Airport(BaseModel):
    iata: str
    name: str
    city: str
    country: str


class DestinationDeal(BaseModel):
    destination: str
    destination_label: str = ""
    price: float
    currency: str
    depart_date: date
    return_date: date | None = None
    deep_link: str | None = None


class Alert(BaseModel):
    id: int
    watch_id: int
    price: float
    currency: str
    message: str
    delivered_to: str = ""
    created_at: str
