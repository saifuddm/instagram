# Instagram Reel Scraper API Service

## Overview

Transform the current Instagram reel scraper into a REST API service that accepts an Instagram URL and returns either JSON or Markdown formatted content.

---

## Tech Stack Options

| Option        | Pros                                                         | Cons                             |
| ------------- | ------------------------------------------------------------ | -------------------------------- |
| **FastAPI**   | Fast, async support, auto-generates OpenAPI docs, type hints | Slightly more complex setup      |
| **Flask**     | Simple, lightweight, easy to learn                           | No async by default, manual docs |
| **Starlette** | Lightweight async, FastAPI is built on it                    | Less features than FastAPI       |

**Recommendation:** FastAPI - best balance of simplicity, performance, and automatic API documentation.

---

## API Design

### Endpoint

```
POST /api/scrape
```

### Request Body

```json
{
  "url": "https://www.instagram.com/reel/DSmdCsLCIhb/",
  "format": "json"  // or "markdown"
}
```

### Response Formats

#### JSON Response (`format: "json"`)

```json
{
  "success": true,
  "data": {
    "url": "https://www.instagram.com/reel/DSmdCsLCIhb/",
    "likes": "724",
    "comments": "6",
    "meta": "alexgori.tech on December 23, 2025",
    "description": "Not because kids ruin anything ...",
    "thumbnail": "https://...",
    "title": "Instagram Reel by @alexgori.tech"
  }
}
```

#### Markdown Response (`format: "markdown"`)

```json
{
  "success": true,
  "content": "# Instagram Reel\n\n**Likes:** 724\n\n..."
}
```

### Error Response

```json
{
  "success": false,
  "error": "Invalid Instagram URL",
  "code": "INVALID_URL"
}
```

---

## Project Structure

```
instagram/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── routes/
│   │   ├── __init__.py
│   │   └── scrape.py        # Scrape endpoint
│   ├── services/
│   │   ├── __init__.py
│   │   └── instagram.py     # Instagram scraping logic (refactored)
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py       # Pydantic models for request/response
│   └── utils/
│       ├── __init__.py
│       └── formatters.py    # JSON/Markdown formatters
├── requirements.txt
├── .env                     # Environment variables
└── README.md
```

---

## Dependencies to Add

```txt
# requirements.txt
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
fastapi>=0.109.0
uvicorn>=0.27.0          # ASGI server to run FastAPI
pydantic>=2.0.0          # Data validation (comes with FastAPI)
python-dotenv>=1.0.0     # Environment variables
```

---

## Implementation Steps

### Phase 1: Refactor Current Code
- [ ] Extract scraping logic into a reusable service class
- [ ] Create separate formatter functions for JSON and Markdown
- [ ] Add URL validation for Instagram links

### Phase 2: Build API Layer
- [ ] Set up FastAPI application
- [ ] Create Pydantic models for request/response validation
- [ ] Implement `/api/scrape` endpoint
- [ ] Add error handling middleware

### Phase 3: Enhancements
- [ ] Add rate limiting (prevent abuse)
- [ ] Add caching (avoid re-scraping same URL)
- [ ] Add request logging
- [ ] Add health check endpoint (`/health`)

### Phase 4: Deployment Ready
- [ ] Add CORS configuration
- [ ] Add environment-based configuration
- [ ] Create Dockerfile (optional)
- [ ] Add API documentation customization

---

## Example Usage

### cURL

```bash
# Get JSON response
curl -X POST http://localhost:8000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.instagram.com/reel/DSmdCsLCIhb/", "format": "json"}'

# Get Markdown response
curl -X POST http://localhost:8000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.instagram.com/reel/DSmdCsLCIhb/", "format": "markdown"}'
```

### Python

```python
import requests

response = requests.post(
    "http://localhost:8000/api/scrape",
    json={
        "url": "https://www.instagram.com/reel/DSmdCsLCIhb/",
        "format": "json"
    }
)
print(response.json())
```

### JavaScript (fetch)

```javascript
const response = await fetch('http://localhost:8000/api/scrape', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    url: 'https://www.instagram.com/reel/DSmdCsLCIhb/',
    format: 'markdown'
  })
});
const data = await response.json();
```

---

## Considerations

### Rate Limiting
Instagram may block or rate-limit requests. Consider:
- Adding delays between requests
- Rotating User-Agent headers
- Using a proxy rotation service for production

### Caching
- Cache responses for a set duration (e.g., 5 minutes)
- Use Redis or in-memory cache for quick lookups
- Reduces load on Instagram and speeds up repeat requests

### Error Handling
| Error         | HTTP Code | Description                         |
| ------------- | --------- | ----------------------------------- |
| Invalid URL   | 400       | URL doesn't match Instagram pattern |
| Scrape Failed | 502       | Instagram returned an error         |
| Rate Limited  | 429       | Too many requests                   |
| Server Error  | 500       | Internal processing error           |

### Security
- Validate and sanitize all input URLs
- Don't expose internal errors to clients
- Consider adding API key authentication for production

---

## Running the API

```bash
# Development
uvicorn app.main:app --reload --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

API docs will be available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Next Steps

Would you like me to implement this API? I can:
1. Start with a minimal working version (single file)
2. Build the full structured version (multiple files)

Let me know which approach you prefer!

