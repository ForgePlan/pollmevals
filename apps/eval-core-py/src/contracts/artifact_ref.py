"""Pydantic v2 model for content-addressed artifact references.

An ArtifactRef records where one output file lives and its integrity hash.
URI scheme:
  v0.1 local: file://artifacts/runs/{run_hash}/evals/{eval_id}/{type}-{sha256}.{ext}
  v0.2+ R2:   s3://pollmevals-runs/...

The sha256 field is the hash of the file content, not the run hash; both are
hex-lowercase 64 chars but they refer to different things.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

_ContentSha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class ArtifactRef(BaseModel):
    """Reference to one content-addressed artifact produced by an Eval.

    sha256: hex-lowercase SHA-256 of the file contents.
    size_bytes: raw byte count of the stored file.
    uri: storage URI (local file:// in v0.1, R2 s3:// in v0.2+).
    mime_type: standard MIME type (text/plain, application/json, …).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    sha256: _ContentSha256
    size_bytes: int = Field(ge=0)
    uri: str
    mime_type: str
