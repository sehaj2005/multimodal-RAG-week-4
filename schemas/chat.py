from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)


class Source(BaseModel):
    file_id: int
    filename: str
    file_type: str
    chunk_index: int
    excerpt: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]


class ChatHistoryResponse(BaseModel):
    id: int
    role: str
    content: str
    sources: list | None = None
