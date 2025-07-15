# backend/api/links.py

from typing import List, Dict, Annotated
from pydantic import HttpUrl

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
    BackgroundTasks,
    Body,
)

from backend.api.dependencies import get_current_user
from backend.core.logging_config import logger
from backend.core.models import WebLinkOut
from backend.db import link_manager
from backend.services.web_scraper import scrape_and_embed_links

router = APIRouter(prefix="/links", tags=["Web Link Management"])


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def submit_links_for_scraping(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Annotated[Dict, Depends(get_current_user)],
    urls: List[HttpUrl] = Body(
        ..., embed=True, description="A list of URLs to be scraped."
    ),
):
    """
    Accepts a list of URLs and triggers a background task to scrape,
    process, and embed their content.
    """
    user_email = current_user["email"]
    logger.info(f"User '{user_email}' submitted {len(urls)} URLs for scraping.")

    # Convert HttpUrl objects back to strings for the background task
    url_strings = [str(url) for url in urls]

    background_tasks.add_task(
        scrape_and_embed_links, urls=url_strings, owner_email=user_email
    )

    return {
        "message": f"{len(urls)} URL(s) received and are being processed in the background."
    }


@router.get("/", response_model=List[WebLinkOut])
async def list_user_links(
    request: Request, current_user: Annotated[Dict, Depends(get_current_user)]
):
    """Retrieves a list of all web links submitted by the current user."""
    links = await link_manager.get_links_by_owner(request.app.db, current_user["email"])
    return [WebLinkOut.model_validate(link) for link in links]


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(
    request: Request,
    link_id: str,
    current_user: Annotated[Dict, Depends(get_current_user)],
):
    """Deletes a specific web link owned by the current user."""
    link_to_delete = await link_manager.get_link_by_id(request.app.db, link_id)
    if not link_to_delete or link_to_delete["owner_email"] != current_user["email"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Web link not found."
        )

    success = await link_manager.delete_link_record(request.app.db, link_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete web link record.",
        )

    return None
