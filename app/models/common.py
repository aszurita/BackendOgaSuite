from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def build(cls, data: list[T], total: int, page: int, page_size: int) -> "PaginatedResponse[T]":
        total_pages = max(1, (total + page_size - 1) // page_size)
        return cls(data=data, total=total, page=page, page_size=page_size, total_pages=total_pages)


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None


class HealthCheck(BaseModel):
    status: str
    db_connected: bool
    version: str = "1.0.0"


class OkResponse(BaseModel):
    ok: bool = True
    message: str | None = None
