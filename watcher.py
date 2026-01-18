#!/usr/bin/env python3
"""
Instagram Watcher - Monitors a queue file for Instagram URLs and processes them.
Automatically downloads videos, compresses them, and creates markdown notes.
Optionally enhances notes with AI to generate better titles, tags, and summaries.

All paths are configurable via .env file. See config.py for details.
"""

import re
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from fetch_instagram import process_instagram_url
from config import (
    AUTO_ENHANCE,
    NOTES_DIR,
    ATTACHMENTS_DIR,
    TEMP_DIR,
    QUEUE_FILE,
    ensure_directories,
    validate_config as validate_ai_config,
)

# Regex pattern to match Instagram URLs
INSTAGRAM_URL_PATTERN = r'https?://(?:www\.)?instagram\.com/(?:reel|p)/[\w-]+'


class InstagramQueueHandler(FileSystemEventHandler):
    """Handles file system events for the Instagram queue file."""

    def __init__(self):
        self.processed_urls = set()
        self.tracking_file = TEMP_DIR / ".processed_urls"
        self._load_processed()

    def _load_processed(self):
        """Load already processed URLs from the tracking file."""
        if self.tracking_file.exists():
            content = self.tracking_file.read_text(encoding="utf-8")
            self.processed_urls = set(line.strip()
                                      for line in content.splitlines() if line.strip())
            print(
                f"📋 Loaded {len(self.processed_urls)} previously processed URLs")

    def _save_processed(self, url: str):
        """Save a processed URL to the tracking file."""
        self.processed_urls.add(url)
        self.tracking_file.parent.mkdir(parents=True, exist_ok=True)
        self.tracking_file.write_text(
            "\n".join(sorted(self.processed_urls)), encoding="utf-8")

    def on_modified(self, event):
        """Called when a file in the watched directory is modified."""
        # Only process if it's our queue file
        if Path(event.src_path).resolve() != QUEUE_FILE.resolve():
            return

        print(f"\n📝 Queue file modified, checking for new URLs...")
        self.process_queue()

    def process_queue(self):
        """Scan the queue file for new Instagram URLs and process them."""
        if not QUEUE_FILE.exists():
            print(f"⚠️  Queue file not found: {QUEUE_FILE}")
            return

        content = QUEUE_FILE.read_text(encoding="utf-8")
        urls = re.findall(INSTAGRAM_URL_PATTERN, content)

        # Filter out already processed URLs
        new_urls = [url for url in urls if url not in self.processed_urls]

        if not new_urls:
            print("✅ No new URLs to process")
            return

        print(f"\n🆕 Found {len(new_urls)} new URL(s) to process")

        for url in new_urls:
            self._process_url(url)

    def _process_url(self, url: str):
        """Process a single Instagram URL."""
        print(f"\n{'=' * 60}")
        print(f"🔄 Processing: {url}")
        print('=' * 60)

        try:
            result = process_instagram_url(
                url=url,
                notes_dir=NOTES_DIR,
                attachments_dir=ATTACHMENTS_DIR,
                compress=True,
                save_raw_html=False,
                temp_dir=TEMP_DIR
            )

            if result["success"]:
                self._save_processed(url)
                self._update_queue_status(url, success=True)
                print(f"\n✅ Successfully processed: {url}")

                # AI Enhancement (if enabled)
                if AUTO_ENHANCE and validate_ai_config():
                    self._enhance_with_ai(result)
            else:
                self._update_queue_status(
                    url, success=False, error=result.get("error"))
                print(f"\n❌ Failed to process: {url}")

        except Exception as e:
            self._update_queue_status(url, success=False, error=str(e))
            print(f"\n❌ Error processing {url}: {e}")

    def _enhance_with_ai(self, result: dict):
        """Enhance the downloaded reel with AI."""
        try:
            from ai_enhancer import enhance_content

            print(f"\n🤖 Running AI enhancement...")
            enhance_result = enhance_content(
                markdown_path=result["markdown_path"],
                video_path=result.get("video_path")
            )

            if enhance_result["success"]:
                print(f"✨ AI enhancement complete!")
            else:
                print(
                    f"⚠️  AI enhancement failed: {enhance_result.get('error')}")

        except ImportError:
            print("⚠️  AI enhancer not available (missing dependencies)")
        except Exception as e:
            print(f"⚠️  AI enhancement error: {e}")

    def _update_queue_status(self, url: str, success: bool, error: str | None = None):
        """Update the queue file to mark URL as processed or failed."""
        if not QUEUE_FILE.exists():
            return

        content = QUEUE_FILE.read_text(encoding="utf-8")

        # Find the URL and add a status marker
        if success:
            # Mark as done with checkmark
            new_content = content.replace(url, f"✅ {url}")
        else:
            # Mark as failed
            error_msg = f" (Error: {error})" if error else ""
            new_content = content.replace(url, f"❌ {url}{error_msg}")

        if new_content != content:
            QUEUE_FILE.write_text(new_content, encoding="utf-8")


def create_queue_file_if_missing():
    """Create the queue file with a template if it doesn't exist."""
    if not QUEUE_FILE.exists():
        QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        template = f"""# Instagram Queue

Paste Instagram URLs below. They will be automatically processed.

---

## How to use
1. Paste an Instagram reel/post URL anywhere in this file
2. The watcher will detect it and download the video
3. A markdown note will be created in `{NOTES_DIR}`
4. The compressed video will be saved in `{ATTACHMENTS_DIR}`
5. Processed URLs will be marked with ✅

---

## Queue

"""
        QUEUE_FILE.write_text(template, encoding="utf-8")
        print(f"📄 Created queue file: {QUEUE_FILE}")


def main():
    """Main entry point for the watcher."""
    print("=" * 60)
    print("🎬 Instagram Watcher")
    print("=" * 60)
    print(f"\n📝 Queue file: {QUEUE_FILE}")
    print(f"📓 Notes output: {NOTES_DIR}")
    print(f"🎥 Videos output: {ATTACHMENTS_DIR}")
    print(f"📂 Temp directory: {TEMP_DIR}")

    # Show AI enhancement status
    if AUTO_ENHANCE:
        if validate_ai_config():
            print("🤖 AI Enhancement: Enabled")
        else:
            print("🤖 AI Enhancement: Disabled (missing GOOGLE_API_KEY)")
    else:
        print("🤖 AI Enhancement: Disabled")
    print()

    # Ensure directories exist
    ensure_directories()

    # Create queue file if it doesn't exist
    create_queue_file_if_missing()

    # Set up the file watcher
    event_handler = InstagramQueueHandler()
    observer = Observer()

    # Watch the directory containing the queue file
    watch_dir = str(QUEUE_FILE.parent)
    observer.schedule(event_handler, watch_dir, recursive=False)

    print(f"👀 Watching: {QUEUE_FILE}")
    print("\n💡 Add Instagram URLs to the queue file and they'll be processed automatically!")
    print("   Press Ctrl+C to stop.\n")

    # Process any existing unprocessed URLs on startup
    print("🔍 Checking for existing unprocessed URLs...")
    event_handler.process_queue()

    # Start watching
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n👋 Stopping watcher...")
        observer.stop()

    observer.join()
    print("✅ Watcher stopped")


if __name__ == "__main__":
    main()
