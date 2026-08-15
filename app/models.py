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

    @field_validator("origin", "destination", "currency")
    @classmethod
    def upper(cls, value: str) -> str:
        return value.upper()

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
    checked_at: str


class Watch(BaseModel):
    id: int
    origin: str
    destination: str
    depart_date: date
    return_date: date | None
    adults: int
    currency: str
    target_price: float | None
    active: bool
    created_at: str
    latest_price: float | None = None
    lowest_price: float | None = None
    checks: int = 0


class Alert(BaseModel):
    id: int
    watch_id: int
    price: float
    currency: str
    message: str
    delivered_to: str = ""
    created_at: str
