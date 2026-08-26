"""Pydantic request/response models."""

from pydantic import BaseModel

# Example models — replace with your own.

class ItemCreate(BaseModel):
    name: str


class ItemResponse(BaseModel):
    id: int
    name: str
    created_at: str
