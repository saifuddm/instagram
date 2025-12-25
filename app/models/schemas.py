"""
Pydantic models for request/response validation.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re


class ResponseFormat(str, Enum):
    """Supported response formats."""
    JSON = "json"
    MARKDOWN = "markdown"


class ScrapeRequest(BaseModel):
    """Request model for the scrape endpoint."""

    url: str = Field(
        ...,
        description="Instagram reel URL to scrape",
        examples=["https://www.instagram.com/reel/DSmdCsLCIhb/"]
    )
    format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="Response format: 'json' or 'markdown'"
    )

    @field_validator("url")
    @classmethod
    def validate_instagram_url(cls, v: str) -> str:
        """Validate that the URL is a valid Instagram reel/post URL."""
        pattern = r'^https?://(www\.)?instagram\.com/(reel|p)/[\w-]+/?$'
        if not re.match(pattern, v):
            raise ValueError(
                "Invalid Instagram URL. Must be a reel or post URL like: "
                "https://www.instagram.com/reel/ABC123/"
            )
        return v


class ReelData(BaseModel):
    """Structured data extracted from an Instagram reel."""

    url: str = Field(..., description="Original Instagram URL")
    likes: str = Field(default="N/A", description="Number of likes")
    comments: str = Field(default="N/A", description="Number of comments")
    meta: str = Field(default="N/A", description="Username and date info")
    description: str = Field(
        default="N/A", description="Post description/caption")
    thumbnail: Optional[str] = Field(
        default=None, description="Thumbnail image URL")
    title: Optional[str] = Field(default=None, description="Post title")
    video_url: Optional[str] = Field(
        default=None, description="Direct video URL if available")


class ScrapeResponse(BaseModel):
    """Successful response model."""

    success: bool = Field(
        default=True, description="Whether the request was successful")
    data: Optional[ReelData] = Field(
        default=None, description="Extracted reel data (JSON format)")
    content: Optional[str] = Field(
        default=None, description="Markdown content (markdown format)")


class ErrorResponse(BaseModel):
    """Error response model."""

    success: bool = Field(default=False, description="Always false for errors")
    error: str = Field(..., description="Human-readable error message")
    code: str = Field(..., description="Error code for programmatic handling")


# Error codes
class ErrorCode:
    """Standard error codes for the API."""
    INVALID_URL = "INVALID_URL"
    SCRAPE_FAILED = "SCRAPE_FAILED"
    PARSE_ERROR = "PARSE_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
