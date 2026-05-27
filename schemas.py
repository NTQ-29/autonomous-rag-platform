from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class VectorPayload(BaseModel):
    """
    Schema for inserting items directly into an Amazon S3 Vector Index.
    """
    key: str = Field(..., description="Unique identifier for the vector chunk (e.g., doc_id#chunk_0)")
    vector: List[float] = Field(..., description="The high-dimensional embedding array (e.g., 1536 dimensions for OpenAI)")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Key-value filtering tags (e.g., {'source': 'manual.pdf', 'project': 'autonomous-rag'})"
    )

class VectorQueryResult(BaseModel):
    """
    Schema representing the structure returned during an S3 Vector API query search.
    """
    key: str
    score: float = Field(..., description="The similarity relevance score (Cosine or Euclidean proximity)")
    metadata: Optional[Dict[str, Any]] = None