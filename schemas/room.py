from pydantic import BaseModel, Field


class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None


class RoomResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    owner_id: int