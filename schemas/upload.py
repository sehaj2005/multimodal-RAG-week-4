from pydantic import BaseModel


class UploadResponse(BaseModel):
    file_id: int
    chunks_created: int
    status: str