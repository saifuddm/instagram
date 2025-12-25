from fastapi import FastAPI, HTTPException
from app.services.instagram import InstagramScraper, FetchError, ParseError
from app.models.schemas import ScrapeRequest, ResponseFormat, ScrapeResponse
from app.utils.formatters import format_as_markdown, format_as_json

app = FastAPI(
    title="Instagram Scraper API",
    description="Scrape Instagram reels and get structured data or markdown",
    version="1.0.0",
)
scraper = InstagramScraper()


@app.post("/api/scrape/instagram", response_model=ScrapeResponse)
async def scrape_instagram(request: ScrapeRequest):
    try:
        scraped_data, parsed_desc = scraper.scrape(request.url)
    except FetchError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except ParseError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if request.format == ResponseFormat.MARKDOWN:
        content = format_as_markdown(request.url, scraped_data, parsed_desc)
        return ScrapeResponse(success=True, content=content)
    else:
        data = format_as_json(request.url, scraped_data, parsed_desc)
        return ScrapeResponse(success=True, data=data)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
