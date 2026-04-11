from pydantic import BaseModel, Field


class ScheduleIngestionRequest(BaseModel):
    source_id: int = Field(gt=0)
    cron: str = Field(default="*/30 * * * *", min_length=5)


class IngestionJobRead(BaseModel):
    id: int
    source_id: int
    cron: str
    status: str


class RunIngestionRequest(BaseModel):
    raw_text: str | None = Field(default=None, min_length=1)


class RunIngestionResponse(BaseModel):
    job_id: int
    chunks_created: int


class RefreshProjectResponse(BaseModel):
    project_id: int
    sources_processed: int
    total_chunks: int
    errors: list[str] = Field(default_factory=list)


class ProjectStatsResponse(BaseModel):
    project_id: int
    sources_count: int
    chunks_count: int
    last_updated: str | None = None
