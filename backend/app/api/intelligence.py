"""Intelligence API - modules, advisories, and LLM chat."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import os
import glob

from app.database import get_session
from app.models import (
    SiteModule, Advisory, ChatMessage, Site, Reading,
    StatusType, CriticalityLevel
)
from app.services.llm import LLMService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


# Pydantic models for requests/responses
class ModuleCreate(BaseModel):
    """Create a module configuration."""
    site_id: str
    module_name: str
    enabled: bool = True


class ModuleUpdate(BaseModel):
    """Update a module configuration."""
    enabled: bool


class ChatRequest(BaseModel):
    """Chat request."""
    message: str


class ChatResponse(BaseModel):
    """Chat response."""
    response: str
    timestamp: datetime


# ==================== Module Management ====================

@router.get("/sites/{site_id}/modules", response_model=List[SiteModule])
async def get_site_modules(site_id: str, session: Session = Depends(get_session)):
    """Get all configured modules for a site."""
    modules = session.exec(
        select(SiteModule)
        .where(SiteModule.site_id == site_id)
        .order_by(SiteModule.module_name)
    ).all()
    return modules


@router.post("/sites/{site_id}/modules", response_model=SiteModule)
async def create_site_module(
    site_id: str,
    module: ModuleCreate,
    session: Session = Depends(get_session)
):
    """Add a module to monitor for a site."""
    # Verify site exists
    site = session.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # Check if module already exists
    existing = session.exec(
        select(SiteModule)
        .where(SiteModule.site_id == site_id)
        .where(SiteModule.module_name == module.module_name)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Module already exists")

    new_module = SiteModule(
        site_id=site_id,
        module_name=module.module_name,
        enabled=module.enabled
    )
    session.add(new_module)
    session.commit()
    session.refresh(new_module)
    return new_module


@router.patch("/modules/{module_id}", response_model=SiteModule)
async def update_site_module(
    module_id: int,
    update: ModuleUpdate,
    session: Session = Depends(get_session)
):
    """Update a module configuration."""
    module = session.get(SiteModule, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    module.enabled = update.enabled
    session.add(module)
    session.commit()
    session.refresh(module)
    return module


@router.delete("/modules/{module_id}")
async def delete_site_module(module_id: int, session: Session = Depends(get_session)):
    """Delete a module configuration."""
    module = session.get(SiteModule, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    session.delete(module)
    session.commit()
    return {"status": "deleted"}


# ==================== Advisories ====================

@router.get("/sites/{site_id}/advisories", response_model=List[Advisory])
async def get_site_advisories(
    site_id: str,
    days: int = 7,
    only_affecting_us: bool = False,
    session: Session = Depends(get_session)
):
    """Get advisories for a site."""
    query = select(Advisory).where(Advisory.site_id == site_id)

    # Filter by date
    since = datetime.utcnow() - timedelta(days=days)
    query = query.where(Advisory.created_at >= since)

    # Filter by relevance
    if only_affecting_us:
        query = query.where(Advisory.affects_us == True)

    advisories = session.exec(query.order_by(Advisory.created_at.desc())).all()
    return advisories


@router.get("/advisories/summary")
async def get_advisories_summary(session: Session = Depends(get_session)):
    """Get summary of all advisories."""
    # Get advisories from last 24 hours
    since = datetime.utcnow() - timedelta(hours=24)

    all_advisories = session.exec(
        select(Advisory)
        .where(Advisory.created_at >= since)
        .order_by(Advisory.created_at.desc())
    ).all()

    affecting_us = [a for a in all_advisories if a.affects_us]

    by_criticality = {
        "high": len([a for a in affecting_us if a.criticality == CriticalityLevel.HIGH]),
        "medium": len([a for a in affecting_us if a.criticality == CriticalityLevel.MEDIUM]),
        "low": len([a for a in affecting_us if a.criticality == CriticalityLevel.LOW]),
    }

    return {
        "total": len(all_advisories),
        "affecting_us": len(affecting_us),
        "by_criticality": by_criticality,
        "recent": [
            {
                "id": a.id,
                "site_id": a.site_id,
                "title": a.title,
                "criticality": a.criticality,
                "affects_us": a.affects_us,
                "affected_modules": a.affected_modules,
                "created_at": a.created_at
            }
            for a in affecting_us[:5]
        ]
    }


# ==================== Chat ====================

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, session: Session = Depends(get_session)):
    """Chat with AI about status dashboard data."""
    # Get context data
    context = await _get_chat_context(session)

    # Get recent chat history
    recent_messages = session.exec(
        select(ChatMessage)
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
    ).all()

    # Build message history for LLM (reverse to chronological order)
    messages = [
        {"role": msg.role, "content": msg.content}
        for msg in reversed(recent_messages)
    ]

    # Add user message
    messages.append({"role": "user", "content": request.message})

    # Get LLM response
    response_text = await LLMService.chat(messages, context)

    # Save user message
    user_msg = ChatMessage(
        role="user",
        content=request.message,
        context_data=context
    )
    session.add(user_msg)

    # Save assistant response
    assistant_msg = ChatMessage(
        role="assistant",
        content=response_text,
        context_data={}
    )
    session.add(assistant_msg)

    session.commit()
    session.refresh(assistant_msg)

    return ChatResponse(
        response=response_text,
        timestamp=assistant_msg.created_at
    )


@router.get("/chat/history", response_model=List[ChatMessage])
async def get_chat_history(
    limit: int = 50,
    session: Session = Depends(get_session)
):
    """Get chat history."""
    messages = session.exec(
        select(ChatMessage)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    ).all()
    return list(reversed(messages))


@router.delete("/chat/history")
async def clear_chat_history(session: Session = Depends(get_session)):
    """Clear chat history."""
    session.exec(select(ChatMessage)).all()
    for msg in session.exec(select(ChatMessage)).all():
        session.delete(msg)
    session.commit()
    return {"status": "cleared"}


async def _get_chat_context(session: Session) -> Dict[str, Any]:
    """Get context data for chat."""
    # Get ALL sites with their current status
    all_sites_status = []
    current_issues = []
    sites = session.exec(select(Site).where(Site.is_active == True)).all()

    for site in sites:
        latest_reading = session.exec(
            select(Reading)
            .where(Reading.site_id == site.id)
            .order_by(Reading.created_at.desc())
            .limit(1)
        ).first()

        if latest_reading:
            site_info = {
                "site": site.display_name,
                "status": latest_reading.status.value,
                "summary": latest_reading.summary
            }
            all_sites_status.append(site_info)

            # Also track issues separately
            if latest_reading.status != StatusType.OPERATIONAL:
                current_issues.append(site_info)

    # Get historical readings from last 24 hours (status changes)
    since_24h = datetime.utcnow() - timedelta(hours=24)
    historical_readings = []

    for site in sites:
        readings = session.exec(
            select(Reading)
            .where(Reading.site_id == site.id)
            .where(Reading.created_at >= since_24h)
            .order_by(Reading.created_at.desc())
        ).all()

        # Include all non-operational readings + recent operational changes
        prev_status = None
        included_count = 0
        for reading in readings:
            # Always include non-operational statuses
            if reading.status != StatusType.OPERATIONAL:
                historical_readings.append({
                    "site": site.display_name,
                    "status": reading.status.value,
                    "summary": reading.summary,
                    "timestamp": reading.created_at.isoformat()
                })
                included_count += 1
            # Include status changes (e.g., degraded -> operational)
            elif prev_status and prev_status != reading.status:
                historical_readings.append({
                    "site": site.display_name,
                    "status": reading.status.value,
                    "summary": reading.summary,
                    "timestamp": reading.created_at.isoformat()
                })
                included_count += 1
            # Include first few operational readings for context
            elif included_count < 3:
                historical_readings.append({
                    "site": site.display_name,
                    "status": reading.status.value,
                    "summary": reading.summary,
                    "timestamp": reading.created_at.isoformat()
                })
                included_count += 1

            prev_status = reading.status

            # Limit per service to avoid overwhelming context
            if included_count >= 15:
                break

    # Sort by timestamp descending
    historical_readings.sort(key=lambda x: x["timestamp"], reverse=True)

    # Get recent advisories
    recent_advisories = session.exec(
        select(Advisory)
        .where(Advisory.created_at >= since_24h)
        .where(Advisory.affects_us == True)
        .order_by(Advisory.created_at.desc())
        .limit(10)
    ).all()

    # Get configured modules across all sites
    all_modules = session.exec(
        select(SiteModule)
        .where(SiteModule.enabled == True)
    ).all()

    configured_modules = list(set([m.module_name for m in all_modules]))

    # Collect DownDetector screenshots for vision analysis
    downdetector_images = []
    screenshots_dir = "/data/downdetector_charts"

    if os.path.exists(screenshots_dir):
        for site in sites:
            # Look for recent screenshots for this site
            pattern = os.path.join(screenshots_dir, f"{site.id}_*.png")
            screenshots = glob.glob(pattern)

            # Get the most recent screenshot
            if screenshots:
                screenshots.sort(key=os.path.getmtime, reverse=True)
                latest_screenshot = screenshots[0]

                downdetector_images.append({
                    "site": site.display_name,
                    "site_id": site.id,
                    "path": latest_screenshot,
                    "timestamp": datetime.fromtimestamp(os.path.getmtime(latest_screenshot)).isoformat()
                })

    return {
        "total_services": len(all_sites_status),
        "all_services": all_sites_status,
        "current_issues": current_issues,
        "historical_readings": historical_readings[:200],  # Increased limit for better coverage
        "recent_advisories": [
            {
                "site_id": a.site_id,
                "title": a.title,
                "criticality": a.criticality.value,
                "affected_modules": a.affected_modules
            }
            for a in recent_advisories
        ],
        "configured_modules": configured_modules,
        "downdetector_images": downdetector_images,
        "timestamp": datetime.utcnow().isoformat()
    }


# ==================== Demo/Test Endpoint ====================

@router.post("/analyze-demo")
async def analyze_demo_advisory(session: Session = Depends(get_session)):
    """Demo endpoint to test advisory analysis."""
    # Get a sample site
    site = session.exec(select(Site).limit(1)).first()
    if not site:
        raise HTTPException(status_code=404, detail="No sites found")

    # Get configured modules for this site
    modules = session.exec(
        select(SiteModule)
        .where(SiteModule.site_id == site.id)
        .where(SiteModule.enabled == True)
    ).all()

    module_names = [m.module_name for m in modules]

    # Demo advisory
    result = await LLMService.analyze_advisory(
        title="Exchange Online experiencing delays",
        description="Users may experience delays when sending or receiving emails through Exchange Online. We are investigating the issue.",
        severity="Medium",
        configured_modules=module_names,
        service_name=site.display_name
    )

    return {
        "site": site.display_name,
        "configured_modules": module_names,
        "analysis": result
    }
