#!/usr/bin/env python3
"""
AI-Powered Instagram Reel Content Enhancer.

Uses Google Gemini to analyze Instagram reels and generate clean, 
well-structured Obsidian notes with proper titles, tags, and references.

Usage:
    python ai_enhancer.py path/to/reel.md path/to/video.mp4
    python ai_enhancer.py path/to/reel.md path/to/video.mp4 --force-video
    python ai_enhancer.py path/to/reel.md path/to/video.mp4 --text-only
    python ai_enhancer.py path/to/reel.md path/to/video.mp4 --dry-run
"""

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from config import (
    GOOGLE_API_KEY,
    QUALITY_CHECK_MODEL,
    ENHANCEMENT_MODEL,
    validate_config,
)


# =============================================================================
# Pydantic Schemas for Structured Outputs
# =============================================================================

class QualityCheckResponse(BaseModel):
    """Response from quality check (Gemini 2.5 Flash Lite)"""
    has_sufficient_detail: bool = Field(
        description="True if the description clearly explains the content"
    )
    reasoning: str = Field(
        description="Brief explanation of why the description is or isn't sufficient"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score from 0.0 to 1.0"
    )


class Tags(BaseModel):
    """Obsidian tags organized by category"""
    topic: list[str] = Field(
        default_factory=list,
        description="Topic tags like 'programming', 'python', 'fitness'"
    )
    content_type: list[str] = Field(
        default_factory=list,
        description="Content type tags like 'tutorial', 'tips', 'motivation'"
    )
    action: list[str] = Field(
        default_factory=list,
        description="Action tags like 'todo', 'reference', 'try-later'"
    )


class Reference(BaseModel):
    """A reference link to related resources"""
    title: str = Field(description="Title of the reference")
    url: str = Field(description="URL to the resource")
    description: str = Field(
        description="Brief description of what the resource covers")


class EnhancedContent(BaseModel):
    """Response from content enhancement"""
    title: str = Field(description="Clear, descriptive title (not clickbait)")
    summary: str = Field(description="Concise summary of the actual content")
    key_points: list[str] = Field(
        default_factory=list,
        description="Key points as actionable bullet points"
    )
    tags: Tags = Field(default_factory=Tags,
                       description="Obsidian tags by category")
    references: list[Reference] = Field(
        default_factory=list,
        description="2-3 reference links to related resources"
    )
    transcript: Optional[str] = Field(
        default=None,
        description="Full transcript of spoken content (only if audio was analyzed)"
    )


# =============================================================================
# Prompts
# =============================================================================

QUALITY_CHECK_PROMPT = """Analyze this Instagram reel description. Does it contain enough detail to understand what the reel teaches or shows?

Description: {description}

Return has_sufficient_detail=true if the description clearly explains the content with actionable information.
Return has_sufficient_detail=false if it's vague, mostly hashtags/emojis, promotional fluff, or doesn't explain what the reel actually teaches."""


TEXT_ENHANCE_PROMPT = """Clean up this Instagram reel description for my personal notes.

Description: {description}
Author: {author}

Generate:
1. A clear, descriptive title (not clickbait) that summarizes what this reel teaches
2. A concise summary of the actual content/tips
3. Key points as bullet points (actionable takeaways)
4. Relevant tags:
   - topic: subject matter tags (e.g., "programming", "python", "fitness", "cooking")
   - content_type: what kind of content (e.g., "tutorial", "tips", "motivation", "review")
   - action: what to do with this (e.g., "todo", "reference", "try-later")
5. 2-3 reference links to related resources (documentation, articles, tutorials, etc.)

Focus on extracting the actual value and making it useful for future reference."""


VIDEO_ANALYZE_PROMPT = """Analyze this Instagram reel video and audio to extract useful information for my notes.

Original description (may be incomplete or vague): {description}

Watch the entire video carefully:
- Listen to any spoken content (voiceover, narration)
- Read any on-screen text, captions, or subtitles
- Note any demonstrations, tutorials, or visual explanations

Generate:
1. A clear, descriptive title based on the ACTUAL content shown/spoken
2. A comprehensive summary of what's taught or demonstrated
3. Key points as bullet points (actionable takeaways someone can use)
4. Relevant tags:
   - topic: subject matter tags (e.g., "programming", "python", "fitness")
   - content_type: what kind of content (e.g., "tutorial", "tips", "motivation")
   - action: what to do with this (e.g., "todo", "reference", "try-later")
5. 2-3 reference links to related resources (documentation, articles, etc.)
6. Full transcript of any spoken content

Focus on extracting the actual value from the video, not just describing what you see."""


# =============================================================================
# Gemini Client
# =============================================================================

class GeminiClient:
    """Unified client for all Gemini operations using google-genai SDK"""

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.quality_check_model = QUALITY_CHECK_MODEL
        self.enhancement_model = ENHANCEMENT_MODEL

    def check_quality(self, description: str) -> QualityCheckResponse:
        """Quick quality check with Flash Lite to determine if video analysis is needed."""
        print(
            f"🔍 Checking description quality with {self.quality_check_model}...")

        response = self.client.models.generate_content(
            model=self.quality_check_model,
            contents=QUALITY_CHECK_PROMPT.format(description=description),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=QualityCheckResponse
            )
        )

        result = QualityCheckResponse.model_validate_json(response.text)
        print(
            f"   Sufficient detail: {result.has_sufficient_detail} (confidence: {result.confidence:.2f})")
        print(f"   Reasoning: {result.reasoning}")
        return result

    def enhance_text(self, description: str, author: str) -> EnhancedContent:
        """Text-only enhancement with Flash when description is sufficient."""
        print(
            f"📝 Enhancing with text-only analysis using {self.enhancement_model}...")

        response = self.client.models.generate_content(
            model=self.enhancement_model,
            contents=TEXT_ENHANCE_PROMPT.format(
                description=description, author=author),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=EnhancedContent
            )
        )

        return EnhancedContent.model_validate_json(response.text)

    def analyze_video(self, video_path: str, description: str) -> EnhancedContent:
        """Full video + audio analysis with Flash when description is insufficient."""
        print(f"🎬 Analyzing video with {self.enhancement_model}...")
        print(f"   Uploading: {video_path}")

        # Upload video file to Gemini
        video_file = self.client.files.upload(file=video_path)
        print(f"   Uploaded as: {video_file.name}")

        # Wait for the file to be processed (become ACTIVE)
        print(f"   Waiting for file to be processed...", end="", flush=True)
        max_wait_seconds = 300  # 5 minutes max
        wait_interval = 2  # Check every 2 seconds
        elapsed = 0

        while elapsed < max_wait_seconds:
            # Get the current file state
            file_info = self.client.files.get(name=video_file.name)
            state = file_info.state.name if hasattr(
                file_info.state, 'name') else str(file_info.state)

            if state == "ACTIVE":
                print(" Ready!")
                break
            elif state == "FAILED":
                raise RuntimeError(
                    f"File processing failed: {video_file.name}")
            else:
                print(".", end="", flush=True)
                time.sleep(wait_interval)
                elapsed += wait_interval
        else:
            raise RuntimeError(
                f"Timeout waiting for file to process after {max_wait_seconds}s")

        try:
            response = self.client.models.generate_content(
                model=self.enhancement_model,
                contents=[
                    video_file,
                    VIDEO_ANALYZE_PROMPT.format(description=description)
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=EnhancedContent
                )
            )

            return EnhancedContent.model_validate_json(response.text)
        finally:
            # Clean up uploaded file
            print(f"   Cleaning up uploaded file...")
            self.client.files.delete(name=video_file.name)


# =============================================================================
# Markdown Parser and Generator
# =============================================================================

class MarkdownNote:
    """Represents an Instagram reel markdown note."""

    def __init__(self, path: Path):
        self.path = path
        self.frontmatter: dict = {}
        self.content: str = ""
        self._parse()

    def _parse(self):
        """Parse the markdown file into frontmatter and content."""
        text = self.path.read_text(encoding="utf-8")

        # Check for YAML frontmatter
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                # Parse frontmatter
                frontmatter_text = parts[1].strip()
                for line in frontmatter_text.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        self.frontmatter[key.strip()] = value.strip()
                self.content = parts[2].strip()
            else:
                self.content = text
        else:
            self.content = text

    @property
    def source_url(self) -> str:
        return self.frontmatter.get("source", "")

    @property
    def author(self) -> str:
        return self.frontmatter.get("author", "N/A")

    @property
    def date(self) -> str:
        return self.frontmatter.get("date", "N/A")

    @property
    def likes(self) -> str:
        return self.frontmatter.get("likes", "N/A")

    @property
    def comments(self) -> str:
        return self.frontmatter.get("comments", "N/A")

    @property
    def description(self) -> str:
        """Extract the description from the content."""
        # Look for the Description section
        match = re.search(
            r"## Description\s*\n\s*(.+?)(?=\n---|\n##|$)", self.content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    @property
    def video_filename(self) -> Optional[str]:
        """Extract the video filename from the embedded video link."""
        match = re.search(r"!\[\[([^\]]+\.mp4)\]\]", self.content)
        if match:
            return match.group(1)
        return None

    @property
    def is_enhanced(self) -> bool:
        """Check if this note has already been AI enhanced."""
        return self.frontmatter.get("ai_enhanced", "").lower() == "true"

    def get_video_path(self, attachments_dir: Path) -> Optional[Path]:
        """Get the full path to the video file."""
        if self.video_filename:
            video_path = attachments_dir / self.video_filename
            if video_path.exists():
                return video_path
        return None


def generate_enhanced_markdown(
    note: MarkdownNote,
    enhanced: EnhancedContent,
    model_used: str
) -> str:
    """Generate the enhanced markdown content."""

    # Build tags list
    all_tags = []
    for topic in enhanced.tags.topic:
        all_tags.append(f"topic/{topic}")
    for ctype in enhanced.tags.content_type:
        all_tags.append(f"type/{ctype}")
    for action in enhanced.tags.action:
        all_tags.append(f"action/{action}")

    # Build frontmatter
    frontmatter_lines = [
        "---",
        f'title: "{enhanced.title}"',
        f"source: {note.source_url}",
        f"author: {note.author}",
        f"date: {note.date}",
        f"likes: {note.likes}",
        f"comments: {note.comments}",
        "tags:",
    ]
    for tag in all_tags:
        frontmatter_lines.append(f"  - {tag}")
    frontmatter_lines.extend([
        "ai_enhanced: true",
        f"ai_model: {model_used}",
        "---",
    ])

    # Build content
    content_lines = [
        "",
        f"# {enhanced.title}",
        "",
        "## Summary",
        "",
        enhanced.summary,
        "",
        "## Key Points",
        "",
    ]
    for point in enhanced.key_points:
        content_lines.append(f"- {point}")

    # Add references
    if enhanced.references:
        content_lines.extend([
            "",
            "## References",
            "",
        ])
        for ref in enhanced.references:
            content_lines.append(
                f"- [{ref.title}]({ref.url}) - {ref.description}")

    # Add transcript if available
    if enhanced.transcript:
        content_lines.extend([
            "",
            "## Transcript",
            "",
            enhanced.transcript,
        ])

    # Add original description
    content_lines.extend([
        "",
        "---",
        "",
        "## Original Description",
        "",
        note.description,
        "",
    ])

    # Add video embed
    if note.video_filename:
        content_lines.extend([
            "## Video",
            "",
            f"![[{note.video_filename}]]",
            "",
        ])

    return "\n".join(frontmatter_lines + content_lines)


# =============================================================================
# Content Enhancer (Main Orchestrator)
# =============================================================================

class ContentEnhancer:
    """Main orchestrator for AI content enhancement."""

    def __init__(self):
        if not validate_config():
            raise ValueError("Invalid configuration - check your .env file")
        self.client = GeminiClient(GOOGLE_API_KEY)

    def enhance(
        self,
        markdown_path: Path,
        video_path: Optional[Path] = None,
        force_video: bool = False,
        text_only: bool = False,
        dry_run: bool = False
    ) -> dict:
        """
        Enhance a single markdown note.

        Args:
            markdown_path: Path to the markdown file
            video_path: Optional path to the video file (auto-detected if not provided)
            force_video: Skip quality check and always analyze video
            text_only: Skip video analysis even if description is poor
            dry_run: Show what would be generated without saving

        Returns:
            Dictionary with enhancement results
        """
        result = {
            "path": str(markdown_path),
            "success": False,
            "enhanced": None,
            "model_used": None,
            "error": None
        }

        try:
            print(f"\n{'=' * 60}")
            print(f"📄 Processing: {markdown_path.name}")
            print("=" * 60)

            # Parse the markdown note
            note = MarkdownNote(markdown_path)

            # Check if already enhanced
            if note.is_enhanced and not force_video:
                print("⏭️  Already enhanced, skipping (use --force-video to re-process)")
                result["error"] = "Already enhanced"
                return result

            # Get description
            description = note.description
            if not description or description == "N/A":
                print("⚠️  No description found in note")
                description = ""
            else:
                print(
                    f"📋 Description: {description[:100]}{'...' if len(description) > 100 else ''}")

            if video_path:
                print(f"🎥 Video: {video_path.name}")
            else:
                print("⚠️  No video file found")

            # Determine analysis path
            enhanced: EnhancedContent
            model_used: str

            if text_only:
                # Force text-only analysis
                print("\n📝 Mode: Text-only (forced)")
                enhanced = self.client.enhance_text(description, note.author)
                model_used = self.client.enhancement_model

            elif force_video and video_path:
                # Force video analysis
                print("\n🎬 Mode: Video analysis (forced)")
                enhanced = self.client.analyze_video(
                    str(video_path), description)
                model_used = self.client.enhancement_model

            elif not video_path:
                # No video available, must use text
                print("\n📝 Mode: Text-only (no video available)")
                enhanced = self.client.enhance_text(description, note.author)
                model_used = self.client.enhancement_model

            else:
                # Run quality check to decide
                print("\n🔍 Running quality check...")
                quality = self.client.check_quality(description)

                if quality.has_sufficient_detail:
                    print("\n📝 Mode: Text-only (description is sufficient)")
                    enhanced = self.client.enhance_text(
                        description, note.author)
                    model_used = self.client.enhancement_model
                else:
                    print("\n🎬 Mode: Video analysis (description insufficient)")
                    enhanced = self.client.analyze_video(
                        str(video_path), description)
                    model_used = self.client.enhancement_model

            # Generate enhanced markdown
            print("\n✨ Generating enhanced markdown...")
            new_content = generate_enhanced_markdown(
                note, enhanced, model_used)

            # Show result
            print(f"\n📌 Title: {enhanced.title}")
            print(
                f"📝 Summary: {enhanced.summary[:100]}{'...' if len(enhanced.summary) > 100 else ''}")
            print(
                f"🏷️  Tags: {', '.join(enhanced.tags.topic + enhanced.tags.content_type + enhanced.tags.action)}")

            if dry_run:
                print("\n🔍 DRY RUN - Would generate:")
                print("-" * 40)
                print(new_content)
                print("-" * 40)
            else:
                # Save the enhanced content
                markdown_path.write_text(new_content, encoding="utf-8")
                print(f"\n✅ Saved enhanced note: {markdown_path}")

            result["success"] = True
            result["enhanced"] = enhanced.model_dump()
            result["model_used"] = model_used

        except Exception as e:
            result["error"] = str(e)
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()

        return result

    def enhance_directory(
        self,
        directory: Path,
        force_video: bool = False,
        text_only: bool = False,
        dry_run: bool = False
    ) -> list[dict]:
        """
        Enhance all markdown notes in a directory.

        Args:
            directory: Path to the directory containing markdown files
            force_video: Skip quality check and always analyze video
            text_only: Skip video analysis even if description is poor
            dry_run: Show what would be generated without saving

        Returns:
            List of enhancement results
        """
        results = []

        # Find all markdown files
        md_files = list(directory.glob("*.md"))

        # Filter out already enhanced files (unless forcing)
        if not force_video:
            unenhanced = []
            for md_file in md_files:
                note = MarkdownNote(md_file)
                if not note.is_enhanced:
                    unenhanced.append(md_file)
            md_files = unenhanced

        print(f"\n📁 Found {len(md_files)} file(s) to process in {directory}")

        for md_file in md_files:
            result = self.enhance(
                markdown_path=md_file,
                force_video=force_video,
                text_only=text_only,
                dry_run=dry_run
            )
            results.append(result)

        # Summary
        successful = sum(1 for r in results if r["success"])
        print(f"\n{'=' * 60}")
        print(
            f"📊 Summary: {successful}/{len(results)} files enhanced successfully")
        print("=" * 60)

        return results


# =============================================================================
# Public API for integration with obsidian_watcher.py
# =============================================================================

def enhance_content(
    markdown_path: str | Path,
    video_path: Optional[str | Path] = None,
    force_video: bool = False,
    text_only: bool = False
) -> dict:
    """
    Enhance a single reel note with AI.

    This is the main entry point for integration with obsidian_watcher.py.

    Args:
        markdown_path: Path to the markdown file
        video_path: Optional path to the video file
        force_video: Skip quality check and always analyze video
        text_only: Skip video analysis

    Returns:
        Dictionary with enhancement results
    """
    enhancer = ContentEnhancer()
    return enhancer.enhance(
        markdown_path=Path(markdown_path),
        video_path=Path(video_path) if video_path else None,
        force_video=force_video,
        text_only=text_only
    )


# =============================================================================
# CLI
# =============================================================================

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AI-Powered Instagram Reel Content Enhancer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ai_enhancer.py path/to/reel.md path/to/video.mp4
  python ai_enhancer.py path/to/reel.md path/to/video.mp4 --force-video
  python ai_enhancer.py path/to/reel.md path/to/video.mp4 --text-only
  python ai_enhancer.py path/to/reel.md path/to/video.mp4 --dry-run
        """
    )

    parser.add_argument(
        "markdown_path",
        help="Path to the markdown file to enhance"
    )
    parser.add_argument(
        "video_path",
        help="Path to the video file"
    )
    parser.add_argument(
        "--force-video", "-f",
        action="store_true",
        help="Skip quality check and always analyze video"
    )
    parser.add_argument(
        "--text-only", "-t",
        action="store_true",
        help="Skip video analysis even if description is poor"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be generated without saving"
    )

    args = parser.parse_args()

    # Validate file paths
    markdown_path = Path(args.markdown_path)
    if not markdown_path.exists():
        print(f"Error: Markdown file not found: {markdown_path}")
        sys.exit(1)

    video_path = Path(args.video_path)
    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}")
        sys.exit(1)

    # Validate config
    if not validate_config():
        sys.exit(1)

    # Create enhancer and process the file
    enhancer = ContentEnhancer()

    result = enhancer.enhance(
        markdown_path=markdown_path,
        video_path=video_path,
        force_video=args.force_video,
        text_only=args.text_only,
        dry_run=args.dry_run
    )

    if not result["success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
