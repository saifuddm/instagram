#!/usr/bin/env python3
"""
Fetch Instagram reel content and save the response to a file.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

# Target Instagram reel URL
URL = "https://www.instagram.com/reel/DNiLOWoxdHI"

# Headers to mimic a browser request (Instagram blocks requests without proper headers)
HEADERS = {
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


def fetch_instagram_reel(url: str) -> requests.Response:
    """
    Fetch the Instagram reel page.

    Args:
        url: The Instagram reel URL to fetch

    Returns:
        The response object from the request
    """
    print(f"Fetching: {url}")
    response = requests.get(url, headers=HEADERS, timeout=30)
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
    print(f"Content-Length: {len(response.content)} bytes")
    return response


def save_response_to_file(response: requests.Response, filename: str) -> None:
    """
    Save the raw response content to a file.

    Args:
        response: The response object to save
        filename: The output filename
    """
    with open(filename, "w", encoding="utf-8") as f:
        f.write(response.text)
    print(f"Raw response saved to: {filename}")


def parse_with_beautifulsoup(html_content: str) -> BeautifulSoup:
    """
    Parse HTML content with BeautifulSoup.

    Args:
        html_content: The HTML string to parse

    Returns:
        A BeautifulSoup object for navigating the parsed HTML
    """
    soup = BeautifulSoup(html_content, "lxml")
    return soup


def extract_basic_info(soup: BeautifulSoup) -> dict:
    """
    Extract basic information from the parsed HTML.

    Args:
        soup: BeautifulSoup object of the page

    Returns:
        Dictionary with extracted information
    """
    info = {}

    # Try to get the meta title
    meta_title = soup.find("meta", attrs={"name": "title"})
    info["title"] = meta_title.get("content", "N/A") if meta_title else "N/A"

    # Try to get meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    info["description"] = meta_desc.get(
        "content", "N/A") if meta_desc else "N/A"

    # Try to get og:title (Open Graph)
    og_title = soup.find("meta", attrs={"property": "og:title"})
    info["og_title"] = og_title.get("content", "N/A") if og_title else "N/A"

    # Try to get og:description
    og_desc = soup.find("meta", attrs={"property": "og:description"})
    info["og_description"] = og_desc.get(
        "content", "N/A") if og_desc else "N/A"

    # Try to get og:image (thumbnail)
    og_image = soup.find("meta", attrs={"property": "og:image"})
    info["og_image"] = og_image.get("content", "N/A") if og_image else "N/A"

    # Try to get og:video (video URL)
    og_video = soup.find("meta", attrs={"property": "og:video"})
    info["og_video"] = og_video.get("content", "N/A") if og_video else "N/A"

    return info


def parse_description(description: str) -> dict:
    """
    Parse the Instagram description into structured data.

    Expected format: "724 likes, 6 comments - alexgori.tech on December 23, 2025: \"Not because kids ruin anything ..."

    Args:
        description: The raw description string

    Returns:
        Dictionary with parsed likes, comments, meta, and description text
    """
    parsed = {
        "likes": "N/A",
        "comments": "N/A",
        "meta": "N/A",
        "description_text": "N/A"
    }

    if not description or description == "N/A":
        return parsed

    # Pattern: "X likes, Y comments - username on Date: \"description text..."
    pattern = r'^([\d,]+)\s+likes?,\s*([\d,]+)\s+comments?\s*-\s*(.+?):\s*["\"]?(.*)$'

    match = re.match(pattern, description, re.DOTALL)

    if match:
        parsed["likes"] = match.group(1).replace(",", "")
        parsed["comments"] = match.group(2).replace(",", "")
        parsed["meta"] = match.group(3).strip()
        # Clean up the description text (remove trailing quote if present)
        desc_text = match.group(4).strip()
        if desc_text.endswith('"') or desc_text.endswith('"'):
            desc_text = desc_text[:-1]
        parsed["description_text"] = desc_text
    else:
        # If pattern doesn't match, try a simpler split
        if " - " in description and ": " in description:
            parts = description.split(" - ", 1)
            if len(parts) == 2:
                # Parse likes and comments from first part
                stats_match = re.match(
                    r'([\d,]+)\s+likes?,\s*([\d,]+)\s+comments?', parts[0])
                if stats_match:
                    parsed["likes"] = stats_match.group(1).replace(",", "")
                    parsed["comments"] = stats_match.group(2).replace(",", "")

                # Parse meta and description from second part
                meta_desc = parts[1].split(": ", 1)
                if len(meta_desc) == 2:
                    parsed["meta"] = meta_desc[0].strip()
                    desc_text = meta_desc[1].strip().strip(
                        '"').strip('"').strip('"')
                    parsed["description_text"] = desc_text

    return parsed


def download_video_with_ytdlp(url: str, output_dir: str = ".") -> str | None:
    """
    Download Instagram video/reel using yt-dlp.

    Args:
        url: The Instagram reel URL
        output_dir: Directory to save the video

    Returns:
        Path to the downloaded video file, or None if failed
    """
    # Check if yt-dlp is installed
    if not shutil.which("yt-dlp"):
        print("\n⚠️  yt-dlp is not installed!")
        print("Install it with: pip install yt-dlp")
        print("Or: winget install yt-dlp")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_template = str(Path(output_dir) / f"reel_{timestamp}.%(ext)s")

    cmd = [
        "yt-dlp",
        "--no-warnings",
        "-o", output_template,
        "--no-playlist",
        url
    ]

    print(f"\n📹 Downloading video with yt-dlp...")
    print(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )

        if result.returncode == 0:
            # Find the downloaded file
            for ext in ["mp4", "webm", "mkv"]:
                video_path = Path(output_dir) / f"reel_{timestamp}.{ext}"
                if video_path.exists():
                    print(f"✅ Video downloaded: {video_path}")
                    return str(video_path)

            # If specific extension not found, search for any matching file
            for f in Path(output_dir).glob(f"reel_{timestamp}.*"):
                if f.suffix.lower() in [".mp4", ".webm", ".mkv", ".mov"]:
                    print(f"✅ Video downloaded: {f}")
                    return str(f)

            print("✅ Download completed but couldn't locate file")
            print(f"stdout: {result.stdout}")
            return None
        else:
            print(f"❌ Download failed!")
            print(f"stderr: {result.stderr}")
            return None

    except subprocess.TimeoutExpired:
        print("❌ Download timed out after 2 minutes")
        return None
    except Exception as e:
        print(f"❌ Error during download: {e}")
        return None


def generate_markdown(info: dict, parsed_desc: dict, url: str) -> str:
    """
    Generate a formatted markdown string from the extracted info.

    Args:
        info: Dictionary with raw extracted information
        parsed_desc: Dictionary with parsed description data
        url: The original Instagram URL

    Returns:
        Formatted markdown string
    """
    md_lines = [
        f"# Instagram Reel",
        f"",
        f"**Source:** {url}",
        f"",
        f"---",
        f"",
        f"**Likes:** {parsed_desc['likes']}",
        f"",
        f"**Comments:** {parsed_desc['comments']}",
        f"",
        f"**Meta:** {parsed_desc['meta']}",
        f"",
        f"---",
        f"",
        f"## Description",
        f"",
        f"{parsed_desc['description_text']}",
        f"",
    ]

    # Add thumbnail if available
    if info.get("og_image") and info["og_image"] != "N/A":
        md_lines.extend([
            f"---",
            f"",
            f"## Thumbnail",
            f"",
            f"![Thumbnail]({info['og_image']})",
            f"",
        ])

    return "\n".join(md_lines)


def main():
    """Main function to orchestrate the fetching and parsing."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Fetch the page
    response = fetch_instagram_reel(URL)

    # Save raw response
    raw_filename = f"response_{timestamp}.html"
    save_response_to_file(response, raw_filename)

    # Parse with BeautifulSoup
    soup = parse_with_beautifulsoup(response.text)

    # Extract and display basic info
    info = extract_basic_info(soup)

    print("\n" + "=" * 50)
    print("EXTRACTED INFORMATION:")
    print("=" * 50)
    for key, value in info.items():
        # Truncate long values for display
        display_value = value[:100] + "..." if len(str(value)) > 100 else value
        print(f"{key}: {display_value}")

    # Save extracted info as JSON
    info_filename = f"extracted_info_{timestamp}.json"
    with open(info_filename, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)
    print(f"\nExtracted info saved to: {info_filename}")

    # Also save a prettified version of the HTML
    pretty_filename = f"response_pretty_{timestamp}.html"
    with open(pretty_filename, "w", encoding="utf-8") as f:
        f.write(soup.prettify())
    print(f"Prettified HTML saved to: {pretty_filename}")

    # Parse the description and generate markdown
    parsed_desc = parse_description(info.get("description", ""))

    print("\n" + "=" * 50)
    print("PARSED DESCRIPTION:")
    print("=" * 50)
    for key, value in parsed_desc.items():
        display_value = value[:100] + "..." if len(str(value)) > 100 else value
        print(f"{key}: {display_value}")

    # Generate and save markdown
    markdown_content = generate_markdown(info, parsed_desc, URL)
    md_filename = f"reel_{timestamp}.md"
    with open(md_filename, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    print(f"\nMarkdown saved to: {md_filename}")

    # Download the video
    print("\n" + "=" * 50)
    print("VIDEO DOWNLOAD:")
    print("=" * 50)
    video_path = download_video_with_ytdlp(URL)
    if video_path:
        print(f"\n🎉 Video saved to: {video_path}")
    else:
        print("\n💡 Tip: If login is required, you can use cookies:")
        print("   yt-dlp --cookies-from-browser chrome <url>")
        print("   yt-dlp --cookies cookies.txt <url>")


if __name__ == "__main__":
    main()
