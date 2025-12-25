"""
Instagram scraping service.

Handles fetching and parsing Instagram reel/post pages.
"""

import re
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup


@dataclass
class ScrapedData:
    """Raw scraped data from Instagram."""

    title: Optional[str] = None
    description: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image: Optional[str] = None
    og_video: Optional[str] = None


@dataclass
class ParsedDescription:
    """Parsed components from Instagram description."""

    likes: str = "N/A"
    comments: str = "N/A"
    meta: str = "N/A"
    description_text: str = "N/A"


class InstagramScraperError(Exception):
    """Base exception for Instagram scraper errors."""
    pass


class FetchError(InstagramScraperError):
    """Raised when fetching the Instagram page fails."""
    pass


class ParseError(InstagramScraperError):
    """Raised when parsing the Instagram page fails."""
    pass


class InstagramScraper:
    """
    Service for scraping Instagram reel/post pages.

    Usage:
        scraper = InstagramScraper()
        result = scraper.scrape("https://www.instagram.com/reel/ABC123/")
    """

    # Headers to mimic a browser request
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

    DEFAULT_TIMEOUT = 30

    def __init__(
        self,
        headers: Optional[dict] = None,
        timeout: int = DEFAULT_TIMEOUT
    ):
        """
        Initialize the Instagram scraper.

        Args:
            headers: Custom headers to use for requests (optional)
            timeout: Request timeout in seconds
        """
        self.headers = headers or self.DEFAULT_HEADERS.copy()
        self.timeout = timeout

    def scrape(self, url: str) -> tuple[ScrapedData, ParsedDescription]:
        """
        Scrape an Instagram reel/post page.

        Args:
            url: The Instagram URL to scrape

        Returns:
            Tuple of (ScrapedData, ParsedDescription)

        Raises:
            FetchError: If the page cannot be fetched
            ParseError: If the page cannot be parsed
        """
        html_content = self._fetch(url)
        scraped_data = self._parse_html(html_content)
        parsed_desc = self._parse_description(scraped_data.description)

        return scraped_data, parsed_desc

    def _fetch(self, url: str) -> str:
        """
        Fetch the Instagram page content.

        Args:
            url: The URL to fetch

        Returns:
            The HTML content as a string

        Raises:
            FetchError: If the request fails
        """
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.text
        except requests.exceptions.Timeout:
            raise FetchError(f"Request timed out after {self.timeout} seconds")
        except requests.exceptions.HTTPError as e:
            raise FetchError(
                f"HTTP error {e.response.status_code}: {e.response.reason}")
        except requests.exceptions.RequestException as e:
            raise FetchError(f"Failed to fetch URL: {str(e)}")

    def _parse_html(self, html_content: str) -> ScrapedData:
        """
        Parse HTML content and extract metadata.

        Args:
            html_content: The HTML string to parse

        Returns:
            ScrapedData with extracted information

        Raises:
            ParseError: If parsing fails
        """
        try:
            soup = BeautifulSoup(html_content, "lxml")

            return ScrapedData(
                title=self._get_meta_content(soup, "name", "title"),
                description=self._get_meta_content(
                    soup, "name", "description"),
                og_title=self._get_meta_content(soup, "property", "og:title"),
                og_description=self._get_meta_content(
                    soup, "property", "og:description"),
                og_image=self._get_meta_content(soup, "property", "og:image"),
                og_video=self._get_meta_content(soup, "property", "og:video"),
            )
        except Exception as e:
            raise ParseError(f"Failed to parse HTML: {str(e)}")

    def _get_meta_content(
        self,
        soup: BeautifulSoup,
        attr_name: str,
        attr_value: str
    ) -> Optional[str]:
        """
        Extract content from a meta tag.

        Args:
            soup: BeautifulSoup object
            attr_name: Attribute name to search (e.g., "name", "property")
            attr_value: Attribute value to match (e.g., "description", "og:image")

        Returns:
            The content attribute value, or None if not found
        """
        tag = soup.find("meta", attrs={attr_name: attr_value})
        if tag:
            return tag.get("content")
        return None

    def _parse_description(self, description: Optional[str]) -> ParsedDescription:
        """
        Parse the Instagram description into structured components.

        Expected format: "724 likes, 6 comments - alexgori.tech on December 23, 2025: \"Not because kids ruin anything ..."

        Args:
            description: The raw description string

        Returns:
            ParsedDescription with extracted components
        """
        if not description:
            return ParsedDescription()

        # Pattern: "X likes, Y comments - username on Date: \"description text..."
        pattern = r'^([\d,]+)\s+likes?,\s*([\d,]+)\s+comments?\s*-\s*(.+?):\s*["\"]?(.*)$'

        match = re.match(pattern, description, re.DOTALL)

        if match:
            desc_text = match.group(4).strip()
            # Clean up trailing quotes
            if desc_text.endswith('"') or desc_text.endswith('"'):
                desc_text = desc_text[:-1]

            return ParsedDescription(
                likes=match.group(1).replace(",", ""),
                comments=match.group(2).replace(",", ""),
                meta=match.group(3).strip(),
                description_text=desc_text,
            )

        # Fallback: try simpler split
        if " - " in description and ": " in description:
            return self._parse_description_fallback(description)

        # If nothing matches, return the raw description as description_text
        return ParsedDescription(description_text=description)

    def _parse_description_fallback(self, description: str) -> ParsedDescription:
        """
        Fallback parser for description that doesn't match main pattern.

        Args:
            description: The raw description string

        Returns:
            ParsedDescription with whatever could be extracted
        """
        result = ParsedDescription()

        parts = description.split(" - ", 1)
        if len(parts) != 2:
            return result

        # Parse likes and comments from first part
        stats_match = re.match(
            r'([\d,]+)\s+likes?,\s*([\d,]+)\s+comments?',
            parts[0]
        )
        if stats_match:
            result.likes = stats_match.group(1).replace(",", "")
            result.comments = stats_match.group(2).replace(",", "")

        # Parse meta and description from second part
        meta_desc = parts[1].split(": ", 1)
        if len(meta_desc) == 2:
            result.meta = meta_desc[0].strip()
            desc_text = meta_desc[1].strip().strip('"').strip('"').strip('"')
            result.description_text = desc_text

        return result
