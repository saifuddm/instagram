#!/usr/bin/env python3
"""
Fetch Instagram reel content, download video, and generate markdown.
Can be used as a CLI tool or imported as a module.
"""

import argparse
import requests
from bs4 import BeautifulSoup
import json
import re
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

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
        "author": "N/A",
        "date": "N/A",
        "description_text": "N/A"
    }

    if not description or description == "N/A":
        return parsed

    # Pattern: "X likes, Y comments - username on Date: \"description text..."
    pattern = r'^([\d,]+)\s+likes?,\s*([\d,]+)\s+comments?\s*-\s*(.+?):\s*["\"]?(.*)$'

    match = re.match(pattern, description, re.DOTALL)

    if match:
        # TODO: Check on links and comments as they appear as null
        parsed["likes"] = match.group(1).replace(",", "")
        parsed["comments"] = match.group(2).replace(",", "")
        meta = match.group(3).strip()
        parsed["meta"] = meta

        # Extract author and date from meta (format: "username on Date")
        meta_match = re.match(r'(.+?)\s+on\s+(.+)', meta)
        if meta_match:
            parsed["author"] = meta_match.group(1).strip()
            parsed["date"] = meta_match.group(2).strip()

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
                    meta = meta_desc[0].strip()
                    parsed["meta"] = meta

                    # Extract author and date
                    meta_match = re.match(r'(.+?)\s+on\s+(.+)', meta)
                    if meta_match:
                        parsed["author"] = meta_match.group(1).strip()
                        parsed["date"] = meta_match.group(2).strip()

                    desc_text = meta_desc[1].strip().strip(
                        '"').strip('"').strip('"')
                    parsed["description_text"] = desc_text

    return parsed


def download_video_with_ytdlp(url: str, output_dir: str = ".", filename: str | None = None) -> str | None:
    """
    Download Instagram video/reel using yt-dlp.

    Args:
        url: The Instagram reel URL
        output_dir: Directory to save the video
        filename: Optional custom filename (without extension)

    Returns:
        Path to the downloaded video file, or None if failed
    """
    # Check if yt-dlp is installed
    if not shutil.which("yt-dlp"):
        print("\n⚠️  yt-dlp is not installed!")
        print("Install it with: pip install yt-dlp")
        print("Or: winget install yt-dlp")
        return None

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reel_{timestamp}"

    output_template = str(Path(output_dir) / f"{filename}.%(ext)s")

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
                video_path = Path(output_dir) / f"{filename}.{ext}"
                if video_path.exists():
                    print(f"✅ Video downloaded: {video_path}")
                    return str(video_path)

            # If specific extension not found, search for any matching file
            for f in Path(output_dir).glob(f"{filename}.*"):
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


def compress_video(input_path: str, output_path: str | None = None, crf: int = 28, max_height: int = 720) -> str | None:
    """
    Compress video using ffmpeg with medium quality settings.

    Args:
        input_path: Path to the input video file
        output_path: Path for the compressed output (default: adds _compressed suffix)
        crf: Constant Rate Factor (18-28 recommended, higher = smaller file)
        max_height: Maximum video height in pixels (preserves aspect ratio)

    Returns:
        Path to the compressed video file, or None if failed
    """
    if not shutil.which("ffmpeg"):
        print("\n⚠️  ffmpeg is not installed!")
        print("Install it with: winget install ffmpeg")
        return None

    input_path = Path(input_path)
    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}")
        return None

    if output_path is None:
        final_output_path = input_path.parent / \
            f"{input_path.stem}_compressed.mp4"
    else:
        final_output_path = Path(output_path)

    # Check if input and output are the same - use temp file if so
    replace_original = input_path.resolve() == final_output_path.resolve()
    if replace_original:
        # Use a temporary file for compression, then replace original
        temp_output_path = input_path.parent / \
            f"{input_path.stem}_temp_compressed.mp4"
    else:
        temp_output_path = final_output_path

    # ffmpeg command for medium compression
    # -crf 28: Good quality/size balance
    # -vf scale: Scale to max height while preserving aspect ratio
    # -preset medium: Balanced encoding speed
    # -c:a aac -b:a 128k: Compress audio to 128kbps AAC
    cmd = [
        "ffmpeg",
        "-i", str(input_path),
        "-vf", f"scale=-2:'min({max_height},ih)'",
        "-c:v", "libx264",
        "-crf", str(crf),
        "-preset", "medium",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",  # Enable fast start for web playback
        "-y",  # Overwrite output file
        str(temp_output_path)
    ]

    print(f"\n🗜️  Compressing video with ffmpeg...")
    print(f"Settings: CRF={crf}, max_height={max_height}px")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout for compression
        )

        if result.returncode == 0 and temp_output_path.exists():
            original_size = input_path.stat().st_size
            compressed_size = temp_output_path.stat().st_size
            reduction = (1 - compressed_size / original_size) * 100

            # If we used a temp file, replace the original
            if replace_original:
                input_path.unlink()  # Delete original
                # Rename temp to final
                temp_output_path.rename(final_output_path)
                print(
                    f"✅ Video compressed (replaced original): {final_output_path}")
            else:
                print(f"✅ Video compressed: {final_output_path}")

            print(f"   Original: {original_size / 1024 / 1024:.2f} MB")
            print(f"   Compressed: {compressed_size / 1024 / 1024:.2f} MB")
            print(f"   Reduction: {reduction:.1f}%")
            return str(final_output_path)
        else:
            print(f"❌ Compression failed!")
            print(f"stderr: {result.stderr}")
            # Clean up temp file if it exists
            if temp_output_path.exists() and replace_original:
                temp_output_path.unlink()
            return None

    except subprocess.TimeoutExpired:
        print("❌ Compression timed out after 5 minutes")
        # Clean up temp file if it exists
        if temp_output_path.exists() and replace_original:
            temp_output_path.unlink()
        return None
    except Exception as e:
        print(f"❌ Error during compression: {e}")
        # Clean up temp file if it exists
        if temp_output_path.exists() and replace_original:
            temp_output_path.unlink()
        return None


def generate_markdown(info: dict, parsed_desc: dict, url: str, video_filename: str | None = None) -> str:
    """
    Generate a formatted markdown string from the extracted info.

    Args:
        info: Dictionary with raw extracted information
        parsed_desc: Dictionary with parsed description data
        url: The original Instagram URL
        video_filename: Optional video filename for embedding

    Returns:
        Formatted markdown string
    """
    # Build YAML frontmatter
    frontmatter_lines = [
        "---",
        f"source: {url}",
        f"author: {parsed_desc.get('author', 'N/A')}",
        f"date: {parsed_desc.get('date', 'N/A')}",
        f"likes: {parsed_desc.get('likes', 'N/A')}",
        f"comments: {parsed_desc.get('comments', 'N/A')}",
        "---",
        "",
    ]

    md_lines = frontmatter_lines + [
        "# Instagram Reel",
        "",
        "## Description",
        "",
        f"{parsed_desc['description_text']}",
        "",
    ]

    # Add video embed if available (Obsidian syntax)
    if video_filename:
        md_lines.extend([
            "---",
            "",
            "## Video",
            "",
            f"![[{video_filename}]]",
            "",
        ])

    # Add thumbnail if available
    if info.get("og_image") and info["og_image"] != "N/A":
        md_lines.extend([
            "---",
            "",
            "## Thumbnail",
            "",
            f"![Thumbnail]({info['og_image']})",
            "",
        ])

    return "\n".join(md_lines)


def extract_reel_id(url: str) -> str:
    """Extract the reel ID from an Instagram URL."""
    # Remove trailing slash and get last path segment
    url = url.rstrip('/')
    match = re.search(r'/(?:reel|p)/([\w-]+)', url)
    if match:
        return match.group(1)
    # Fallback: use last segment
    return url.split('/')[-1] or datetime.now().strftime("%Y%m%d_%H%M%S")


def process_instagram_url(
    url: str,
    notes_dir: str | Path = ".",
    attachments_dir: str | Path = ".",
    compress: bool = True,
    save_raw_html: bool = False,
    temp_dir: str | Path | None = None
) -> dict:
    """
    Process a single Instagram URL: fetch metadata, download video, create markdown.

    Args:
        url: Instagram reel/post URL
        notes_dir: Directory to save the markdown note
        attachments_dir: Directory to save the final video file
        compress: Whether to compress the video
        save_raw_html: Whether to save the raw HTML response
        temp_dir: Directory for temporary files (download/compression). 
                  Defaults to current working directory.

    Returns:
        Dictionary with paths to created files and extracted info
    """
    result = {
        "url": url,
        "success": False,
        "markdown_path": None,
        "video_path": None,
        "info": None,
        "error": None
    }

    try:
        notes_dir = Path(notes_dir)
        attachments_dir = Path(attachments_dir)
        temp_dir = Path(temp_dir) if temp_dir else Path.cwd()

        notes_dir.mkdir(parents=True, exist_ok=True)
        attachments_dir.mkdir(parents=True, exist_ok=True)
        temp_dir.mkdir(parents=True, exist_ok=True)

        reel_id = extract_reel_id(url)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Fetch the page
        response = fetch_instagram_reel(url)

        # Optionally save raw HTML
        if save_raw_html:
            # TODO: Change the storing of this raw html file to the temp_dir
            raw_filename = notes_dir / f"response_{reel_id}_{timestamp}.html"
            save_response_to_file(response, str(raw_filename))

        # Parse with BeautifulSoup
        soup = parse_with_beautifulsoup(response.text)

        # Extract info
        info = extract_basic_info(soup)
        parsed_desc = parse_description(info.get("description", ""))
        result["info"] = {**info, **parsed_desc}

        print("\n" + "=" * 50)
        print("EXTRACTED INFORMATION:")
        print("=" * 50)
        for key, value in info.items():
            display_value = str(value)[:100] + \
                "..." if len(str(value)) > 100 else value
            print(f"{key}: {display_value}")

        # Download video to temp directory
        print("\n" + "=" * 50)
        print("VIDEO DOWNLOAD:")
        print("=" * 50)

        video_filename = f"{reel_id}_temp"
        temp_video_path = download_video_with_ytdlp(
            url, str(temp_dir), video_filename)

        final_video_path = None
        if temp_video_path:
            if compress:
                print("\n" + "=" * 50)
                print("VIDEO COMPRESSION:")
                print("=" * 50)
                # Compress to temp directory first
                compressed_temp_path = compress_video(
                    temp_video_path,
                    str(temp_dir / f"{reel_id}_compressed.mp4")
                )
                if compressed_temp_path:
                    # Remove original downloaded file
                    if Path(temp_video_path).exists():
                        Path(temp_video_path).unlink()
                        print(f"🗑️  Removed temp download: {temp_video_path}")

                    # Move compressed file to final destination
                    final_video_path = attachments_dir / f"{reel_id}.mp4"
                    shutil.move(compressed_temp_path, final_video_path)
                    print(f"📦 Moved to attachments: {final_video_path}")
            else:
                # No compression - move directly to attachments
                ext = Path(temp_video_path).suffix
                final_video_path = attachments_dir / f"{reel_id}{ext}"
                shutil.move(temp_video_path, final_video_path)
                print(f"📦 Moved to attachments: {final_video_path}")

        result["video_path"] = str(
            final_video_path) if final_video_path else None
        final_video_filename = final_video_path.name if final_video_path else None

        # Validate: fail if no description AND no video
        has_description = (
            parsed_desc.get("description_text")
            and parsed_desc["description_text"] != "N/A"
            and parsed_desc["description_text"].strip()
        )
        has_video = final_video_path is not None

        if not has_description and not has_video:
            result["error"] = "No description and no video found - nothing to analyze"
            print(f"\n❌ Extraction failed: No description and no video found")
            print("   This reel has no useful content to extract.")
            return result

        # Generate and save markdown
        markdown_content = generate_markdown(
            info, parsed_desc, url, final_video_filename)
        md_path = notes_dir / f"{reel_id}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        print(f"\n✅ Markdown saved to: {md_path}")
        result["markdown_path"] = str(md_path)

        result["success"] = True
        print(f"\n🎉 Successfully processed: {url}")

    except Exception as e:
        result["error"] = str(e)
        print(f"\n❌ Error processing {url}: {e}")

    return result


def main():
    """Main function with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Fetch Instagram reel content, download video, and generate markdown."
    )
    parser.add_argument(
        "url",
        nargs="?",
        default="https://www.instagram.com/reel/DNiLOWoxdHI",
        help="Instagram reel URL to process"
    )
    parser.add_argument(
        "--notes-dir", "-n",
        default="data",
        help="Directory to save markdown notes (default: data)"
    )
    parser.add_argument(
        "--attachments-dir", "-a",
        default="video",
        help="Directory to save video files (default: video)"
    )
    parser.add_argument(
        "--no-compress",
        action="store_true",
        help="Skip video compression"
    )
    parser.add_argument(
        "--save-html",
        action="store_true",
        help="Save raw HTML response"
    )
    parser.add_argument(
        "--temp-dir", "-t",
        default="temp",
        help="Directory for temporary files during download/compression (default: temp)"
    )

    args = parser.parse_args()

    result = process_instagram_url(
        url=args.url,
        notes_dir=args.notes_dir,
        attachments_dir=args.attachments_dir,
        compress=not args.no_compress,
        save_raw_html=args.save_html,
        temp_dir=args.temp_dir
    )

    if not result["success"]:
        print("\n💡 Tip: If login is required, you can use cookies:")
        print("   yt-dlp --cookies-from-browser chrome <url>")
        print("   yt-dlp --cookies cookies.txt <url>")
        exit(1)


if __name__ == "__main__":
    main()
