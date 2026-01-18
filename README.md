# Instagram Reel Downloader

Download Instagram reels, compress videos, and generate Obsidian-ready markdown notes with optional AI enhancement.

## Features

- Download reels via `yt-dlp` with metadata extraction
- Video compression with `ffmpeg` (~70% size reduction)
- Markdown notes with YAML frontmatter
- File watcher for automatic queue processing
- AI enhancement via Google Gemini (titles, tags, summaries)

## Requirements

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/) installed and in PATH
- Google API key (optional, for AI enhancement)

## Installation

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Create a `.env` file (optional):

```env
NOTES_DIR=./data
ATTACHMENTS_DIR=./video
TEMP_DIR=./temp
QUEUE_FILE=./data/Instagram Queue.md
GOOGLE_API_KEY=your-api-key
AUTO_ENHANCE=true
```

---

## Scripts

### `fetch_instagram.py` — Download a single reel

```bash
# Basic usage
python fetch_instagram.py "https://www.instagram.com/reel/ABC123/"

# Custom output directories
python fetch_instagram.py "https://www.instagram.com/reel/ABC123/" \
  --notes-dir ./notes --attachments-dir ./videos

# Skip compression
python fetch_instagram.py "https://www.instagram.com/reel/ABC123/" --no-compress
```

### `watcher.py` — Auto-process queue file

Monitors a markdown file for Instagram URLs and processes them automatically.

```bash
python watcher.py
```

Paste URLs into `Instagram Queue.md` — they'll be downloaded, compressed, and marked as processed.

### `ai_enhancer.py` — Enhance notes with AI

Uses Google Gemini to add titles, tags, and summaries to markdown notes.

```bash
# Enhance a note
python ai_enhancer.py ./data/ABC123.md ./video/ABC123.mp4

# Dry run (preview only)
python ai_enhancer.py ./data/ABC123.md ./video/ABC123.mp4 --dry-run

# Force video analysis
python ai_enhancer.py ./data/ABC123.md ./video/ABC123.mp4 --force-video
```

---

## Disclaimer

This project is provided for **educational and personal use only**. Scraping or downloading content from Instagram may violate their [Terms of Service](https://help.instagram.com/581066165581870). The author is not responsible for how this tool is used or any consequences arising from its use.

- Respect copyright and intellectual property rights
- Only download content you have permission to use
- Be aware of and comply with local laws regarding web scraping
- Use at your own risk