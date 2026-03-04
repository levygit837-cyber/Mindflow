from pydantic import BaseModel, Field

from omnimind_backend.schemas.core.common import LLMProvider


class AppSettings(BaseModel):
    defaultProvider: LLMProvider = "vertexai"
    defaultModel: str = Field(default="gemini-3-flash-preview", min_length=1)
    anthropicApiKey: str = ""
    openaiApiKey: str = ""
    googleApiKey: str = ""
    ollamaBaseUrl: str = "http://localhost:11434"


class SettingsUpdate(BaseModel):
    defaultProvider: LLMProvider | None = None
    defaultModel: str | None = Field(default=None, min_length=1)
    anthropicApiKey: str | None = None
    openaiApiKey: str | None = None
    googleApiKey: str | None = None
    ollamaBaseUrl: str | None = None
