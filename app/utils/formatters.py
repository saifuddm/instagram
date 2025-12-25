"""
Output formatters for Instagram scraper data.

Provides JSON and Markdown formatting for scraped data.
"""

from app.services.instagram import ScrapedData, ParsedDescription
from app.models.schemas import ReelData


def format_as_json(
    url: str,
    scraped_data: ScrapedData,
    parsed_desc: ParsedDescription
) -> ReelData:
    """
    Format scraped data as a structured JSON-ready object.

    Args:
        url: The original Instagram URL
        scraped_data: Raw scraped data from Instagram
        parsed_desc: Parsed description components

    Returns:
        ReelData model ready for JSON serialization
    """
    return ReelData(
        url=url,
        likes=parsed_desc.likes,
        comments=parsed_desc.comments,
        meta=parsed_desc.meta,
        description=parsed_desc.description_text,
        thumbnail=scraped_data.og_image,
        title=scraped_data.og_title or scraped_data.title,
        video_url=scraped_data.og_video,
    )


def format_as_markdown(
    url: str,
    scraped_data: ScrapedData,
    parsed_desc: ParsedDescription
) -> str:
    """
    Format scraped data as a Markdown string.

    Args:
        url: The original Instagram URL
        scraped_data: Raw scraped data from Instagram
        parsed_desc: Parsed description components

    Returns:
        Formatted Markdown string
    """
    lines = [
        "# Instagram Reel",
        "",
        f"**Source:** {url}",
        "",
        "---",
        "",
        f"**Likes:** {parsed_desc.likes}",
        "",
        f"**Comments:** {parsed_desc.comments}",
        "",
        f"**Meta:** {parsed_desc.meta}",
        "",
        "---",
        "",
        "## Description",
        "",
        parsed_desc.description_text,
        "",
    ]

    # Add thumbnail section if available
    if scraped_data.og_image:
        lines.extend([
            "---",
            "",
            "## Thumbnail",
            "",
            f"![Thumbnail]({scraped_data.og_image})",
            "",
        ])

    # Add video URL if available
    if scraped_data.og_video:
        lines.extend([
            "---",
            "",
            "## Video",
            "",
            f"[Direct Video Link]({scraped_data.og_video})",
            "",
        ])

    return "\n".join(lines)
