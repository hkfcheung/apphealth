"""Intelligence API - modules, advisories, and LLM chat."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
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
    # Get context data to provide service information
    context = await _get_chat_context(session)

    # Log context for debugging
    logger.info(f"Chat context: {context.get('total_services', 0)} services, {len(context.get('current_issues', []))} issues, {len(context.get('recent_advisories', []))} advisories")

    # If no services are configured, pass None so AI can answer general questions
    if context.get("total_services", 0) == 0:
        logger.info("No services configured, passing None context")
        context = None

    # Skip chat history for speed
    messages = [{"role": "user", "content": request.message}]

    # Get LLM response
    response_text = await LLMService.chat(messages, context)

    # Skip saving to database for speed
    return ChatResponse(
        response=response_text,
        timestamp=datetime.utcnow()
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
    """Get simplified context data for chat."""
    # Get basic site status - simplified for speed
    all_sites_status = []
    current_issues = []
    historical_readings = []
    sites = session.exec(select(Site).where(Site.is_active == True)).all()

    # Get historical data for recent issues and uptime (last 24 hours for chat context)
    since = datetime.utcnow() - timedelta(hours=24)

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
                "summary": latest_reading.summary or "No details"
            }
            all_sites_status.append(site_info)

            # Also track issues separately
            if latest_reading.status != StatusType.OPERATIONAL:
                current_issues.append(site_info)

        # Get non-operational historical readings (issues only) for last 24h
        # This keeps context small while showing actual problems
        problem_readings = session.exec(
            select(Reading)
            .where(Reading.site_id == site.id)
            .where(Reading.created_at >= since)
            .where(Reading.status != 'operational')
            .order_by(Reading.created_at.desc())
            .limit(10)  # Limit to 10 most recent issues per service
        ).all()

        for reading in problem_readings:
            historical_readings.append({
                "site": site.display_name,
                "status": reading.status.value,
                "summary": reading.summary or "No details",
                "timestamp": reading.created_at.isoformat()
            })

    # Get recent advisories (last 24 hours)
    since = datetime.utcnow() - timedelta(hours=24)
    advisories = session.exec(
        select(Advisory)
        .where(Advisory.created_at >= since)
        .order_by(Advisory.created_at.desc())
    ).all()

    recent_advisories = []
    for adv in advisories:
        recent_advisories.append({
            "site_id": adv.site_id,
            "title": adv.title,
            "criticality": adv.criticality.value,
            "affects_us": adv.affects_us,
            "affected_modules": adv.affected_modules,
            "relevance_reason": adv.relevance_reason
        })

    # Get all configured modules across all sites
    all_modules = session.exec(
        select(SiteModule)
        .where(SiteModule.enabled == True)
    ).all()

    configured_modules = list(set([m.module_name for m in all_modules]))

    return {
        "total_services": len(all_sites_status),
        "all_services": all_sites_status,
        "current_issues": current_issues,
        "recent_advisories": recent_advisories,
        "configured_modules": configured_modules,
        "historical_readings": historical_readings,
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
