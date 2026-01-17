
"""
Processes API - Environmental processes and workflows
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone
import json
import os
import uuid

from app.database import get_db
from app.models.user import User
from app.models.process import Process, ProcessStatus, ProcessPriority
from app.models.checklist_item import ProcessChecklistItem
from app.models.organization import Organization
from app.schemas.processes import (
    ProcessCreate, ProcessUpdate, ProcessResponse,
    ProcessListResponse, ProcessStatusUpdate, ProcessProgressUpdate,
    ProcessStatusEnum, ProcessPriorityEnum
)
from app.dependencies.auth import get_current_active_user, get_organization_from_token
from app.utils.audit_logger import AuditLogger
from app.utils.report_generator import generate_technical_report

router = APIRouter()


def parse_tags(tags_str: Optional[str]) -> Optional[List[str]]:
    """Parse JSON tags string to list."""
    if not tags_str:
        return None
    try:
        return json.loads(tags_str)
    except:
        return None


def serialize_tags(tags: Optional[List[str]]) -> Optional[str]:
    """Serialize tags list to JSON string."""
    if not tags:
        return None
    return json.dumps(tags)


def process_to_response(proc: Process) -> ProcessResponse:
    """Convert Process model to response schema."""
    return ProcessResponse(
        id=proc.id,
        title=proc.title,
        protocol=proc.protocol,
        status=ProcessStatusEnum(proc.status.value),
        priority=ProcessPriorityEnum(proc.priority.value),
        progress=proc.progress,
        responsible=proc.responsible,
        location=proc.location,
        tags=parse_tags(proc.tags),
        summary=proc.summary,
        deadline=proc.deadline,
        created_at=proc.created_at,
        updated_at=proc.updated_at
    )
