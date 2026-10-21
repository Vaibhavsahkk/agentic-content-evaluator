from typing import List, Optional
from pydantic import BaseModel, Field

class ReferenceItem(BaseModel):
    source_id: str = Field(description="Unique stable reference identifier, e.g. REF-01")
    title: str = Field(description="Title of research paper or authoritative documentation")
    url: str = Field(description="Verified URL of the reference")
    authors: Optional[str] = Field(default=None, description="Authors or publisher")
    publication_date: Optional[str] = Field(default=None, description="Original publication date")
    date_verified: str = Field(description="Date verified by engineer (ISO format)")
    claims: List[str] = Field(description="List of verified factual claims supported by this reference")
    excerpt: str = Field(description="Supporting factual excerpt")
    version: str = Field(default="1.0.0", description="Reference pack version")

class ReferencePack(BaseModel):
    pack_name: str
    version: str
    topic: str
    items: List[ReferenceItem]

class ReferenceQuery(BaseModel):
    query: str = Field(min_length=1, max_length=200, description="Lookup search query")
    max_results: int = Field(default=3, ge=1, le=5, description="Maximum number of sources to return (bounded)")

class ReferenceSearchResult(BaseModel):
    source_id: str
    title: str
    url: str
    excerpt: str
    matched_claims: List[str]
