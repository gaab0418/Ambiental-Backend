
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
from app.utils.default_checklist import get_default_checklist_items
from app.utils.n8n_client import trigger_process_webhook

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
    # Calculate checklist stats
    total_items = len(proc.checklist_items)
    completed_items = sum(1 for item in proc.checklist_items if item.is_completed)
    
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
        in_type=proc.in_type,
        summary=proc.summary,
        deadline=proc.deadline,
        created_at=proc.created_at,
        updated_at=proc.updated_at,
        checklist_total=total_items,
        checklist_completed=completed_items,
        checklist_pending=total_items - completed_items
    )


@router.get("", response_model=ProcessListResponse)
async def list_processes(
    request: Request,
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List processes with filters."""
    org_id = get_organization_from_token(request)
    
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required"
        )
    
    query = db.query(Process).filter(Process.organization_id == org_id)
    
    # Apply filters
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            Process.title.ilike(search_pattern) |
            Process.protocol.ilike(search_pattern) |
            Process.summary.ilike(search_pattern)
        )
    
    if status:
        try:
            status_enum = ProcessStatus(status)
            query = query.filter(Process.status == status_enum)
        except ValueError:
            pass
    
    if priority:
        try:
            priority_enum = ProcessPriority(priority)
            query = query.filter(Process.priority == priority_enum)
        except ValueError:
            pass
    
    if from_date:
        try:
            from_dt = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            query = query.filter(Process.created_at >= from_dt)
        except ValueError:
            pass
    
    if to_date:
        try:
            to_dt = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
            query = query.filter(Process.created_at <= to_dt)
        except ValueError:
            pass
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    processes = query.order_by(Process.created_at.desc()).offset(offset).limit(limit).all()
    
    return ProcessListResponse(
        items=[process_to_response(proc) for proc in processes],
        total=total,
        limit=limit,
        offset=offset
    )


@router.post("", response_model=ProcessResponse, status_code=status.HTTP_201_CREATED)
async def create_process(
    request: Request,
    title: str = Form(...),
    protocol: str = Form(...),
    status_val: str = Form("EM_ANDAMENTO", alias="status"),
    priority_val: str = Form("MEDIA", alias="priority"),
    deadline: Optional[str] = Form(None),
    summary: Optional[str] = Form(None),
    responsible: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    in_type: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    file: UploadFile = File(...),  # Mandatory file
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new process with mandatory PDF document."""
    org_id = get_organization_from_token(request)
    
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required"
        )
    
    # Check if protocol already exists
    existing = db.query(Process).filter(Process.protocol == protocol).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Protocol already exists"
        )
    
    # 1. Create Process
    process = Process(
        organization_id=org_id,
        title=title,
        protocol=protocol,
        status=ProcessStatus(status_val),
        priority=ProcessPriority(priority_val),
        progress=0,
        responsible=responsible,
        location=location,
        tags=tags, # Expecting raw JSON string or nothing if coming from form
        summary=summary,
        in_type=in_type,
        deadline=datetime.fromisoformat(deadline.replace('Z', '+00:00')) if deadline else None,
        created_by_user_id=current_user.id
    )
    
    db.add(process)
    db.commit()
    db.refresh(process)

    # 2. Save Document (Reusing logic from documents.py slightly)
    # Validate file type (basic)
    if not file.content_type == "application/pdf":
        # Cleanup process if file is invalid? Or just error?
        # Ideally we rollback, but let's stick to simple flow.
        db.delete(process) 
        db.commit()
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    content = await file.read()
    
    # Storage logic
    from app.api.v1.documents import DOCUMENTS_UPLOAD_DIR
    import os, uuid, hashlib
    from app.models.document import Document, DocumentStatus
    
    file_ext = os.path.splitext(file.filename)[1] if file.filename else ".pdf"
    stored_filename = f"{uuid.uuid4()}{file_ext}"
    org_upload_dir = os.path.join(DOCUMENTS_UPLOAD_DIR, str(org_id))
    os.makedirs(org_upload_dir, exist_ok=True)
    storage_path = os.path.join(org_upload_dir, stored_filename)
    
    with open(storage_path, "wb") as f:
        f.write(content)
        
    checksum = hashlib.sha256(content).hexdigest()
    
    document = Document(
        organization_id=org_id,
        process_id=process.id, # Link to process
        name=f"Anexo Processo - {file.filename}",
        category="PROCESSO_ANEXO",
        status=DocumentStatus.VALIDADO,
        original_filename=file.filename or "process_attachment.pdf",
        stored_filename=stored_filename,
        storage_path=storage_path,
        mime_type=file.content_type or "application/pdf",
        size_bytes=len(content),
        checksum=checksum,
        owner_name=current_user.full_name or "Sistema",
        uploaded_by_user_id=current_user.id
    )
    
    db.add(document)
    db.commit()
    
    # Timeline entry creation removed (deprecated)
    
    # Log audit
    AuditLogger.log_create(
        db=db,
        entity_type="Process",
        entity_id=process.id,
        user_id=current_user.id,
        organization_id=org_id,
        changes={"title": process.title, "protocol": process.protocol, "document": "attached"}
    )
    
    # Note: Checklist items are NOT created automatically. 
    # Users can add checklist items manually via the UI.
    
    db.commit()
    
    # Trigger N8N Webhook (Async, don't block response if it fails, or log error)
    # We pass the auth token from the request headers
    auth_token = request.headers.get("Authorization")
    
    # Run webhook trigger
    try:
        await trigger_process_webhook(
            process_id=process.id,
            file_name=in_type or file.filename, # Use in_type as filename if available, else original filename
            file_path=storage_path,
            auth_token=auth_token
        )
    except Exception as e:
        print(f"Failed to trigger N8N webhook: {e}")
        # We continue even if webhook fails, as process is created

    return process_to_response(process)


@router.get("/{process_id}", response_model=ProcessResponse)
async def get_process(
    request: Request,
    process_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific process."""
    org_id = get_organization_from_token(request)
    
    process = db.query(Process).filter(
        Process.id == process_id,
        Process.organization_id == org_id
    ).first()
    
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process not found"
        )
    
    return process_to_response(process)


@router.put("/{process_id}", response_model=ProcessResponse)
async def update_process(
    request: Request,
    process_id: int,
    process_data: ProcessUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a process."""
    org_id = get_organization_from_token(request)
    
    process = db.query(Process).filter(
        Process.id == process_id,
        Process.organization_id == org_id
    ).first()
    
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process not found"
        )
    
    # Check protocol uniqueness if changing
    if process_data.protocol and process_data.protocol != process.protocol:
        existing = db.query(Process).filter(Process.protocol == process_data.protocol).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Protocol already exists"
            )
    
    # Update fields
    update_data = process_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value:
            setattr(process, field, ProcessStatus(value.value))
        elif field == "priority" and value:
            setattr(process, field, ProcessPriority(value.value))
        elif field == "tags":
            setattr(process, field, serialize_tags(value))
        else:
            setattr(process, field, value)
    
    process.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(process)
    
    # Log audit
    AuditLogger.log_update(
        db=db,
        entity_type="Process",
        entity_id=process.id,
        changes=update_data,
        user_id=current_user.id,
        organization_id=org_id
    )
    
    return process_to_response(process)


@router.put("/{process_id}/status", response_model=ProcessResponse)
async def update_process_status(
    request: Request,
    process_id: int,
    status_data: ProcessStatusUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update the status of a process."""
    org_id = get_organization_from_token(request)
    
    process = db.query(Process).filter(
        Process.id == process_id,
        Process.organization_id == org_id
    ).first()
    
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process not found"
        )
    
    old_status = process.status.value
    new_status = ProcessStatus(status_data.status.value)
    process.status = new_status
    process.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(process)
    
    # Log audit
    AuditLogger.log_update(
        db=db,
        entity_type="Process",
        entity_id=process.id,
        changes={"status": {"old": old_status, "new": new_status.value}},
        user_id=current_user.id,
        organization_id=org_id
    )
    
    return process_to_response(process)


@router.put("/{process_id}/progress", response_model=ProcessResponse)
async def update_process_progress(
    request: Request,
    process_id: int,
    progress_data: ProcessProgressUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update the progress of a process."""
    org_id = get_organization_from_token(request)
    
    process = db.query(Process).filter(
        Process.id == process_id,
        Process.organization_id == org_id
    ).first()
    
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process not found"
        )
    
    old_progress = process.progress
    process.progress = progress_data.progress
    process.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(process)
    
    # Log audit
    AuditLogger.log_update(
        db=db,
        entity_type="Process",
        entity_id=process.id,
        changes={"progress": {"old": old_progress, "new": process.progress}},
        user_id=current_user.id,
        organization_id=org_id
    )
    
    return process_to_response(process)





from app.models.chat_thread import ChatThread

@router.delete("/{process_id}")
async def delete_process(
    request: Request,
    process_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a process."""
    org_id = get_organization_from_token(request)
    
    process = db.query(Process).filter(
        Process.id == process_id,
        Process.organization_id == org_id
    ).first()
    
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process not found"
        )
    
    process_title = process.title
    
    # Log audit before deletion
    AuditLogger.log_delete(
        db=db,
        entity_type="Process",
        entity_id=process.id,
        user_id=current_user.id,
        organization_id=org_id,
        changes={"title": process_title, "protocol": process.protocol}
    )
    
    # Unlink linked chat threads (set process_id to None)
    # ensuring deletion doesn't fail due to FK constraints
    linked_threads = db.query(ChatThread).filter(ChatThread.process_id == process_id).all()
    for thread in linked_threads:
        thread.process_id = None
        # We keep process_code for reference if needed
    
    # Delete process (timeline entries will be cascade deleted)
    db.delete(process)
    db.commit()
    
    return {"message": f"Process '{process_title}' deleted successfully"}




@router.get("/{process_id}/document")
async def get_process_document(
    request: Request,
    process_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get the document linked to a process."""
    org_id = get_organization_from_token(request)
    
    # Get process
    process = db.query(Process).filter(
        Process.id == process_id,
        Process.organization_id == org_id
    ).first()
    
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process not found"
        )
    
    # Get document linked to this process
    from app.models.document import Document
    document = db.query(Document).filter(
        Document.process_id == process_id,
        Document.organization_id == org_id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No document found for this process"
        )
    
    return {
        "id": document.id,
        "name": document.name,
        "original_filename": document.original_filename,
        "mime_type": document.mime_type,
        "size_bytes": document.size_bytes,
        "download_url": f"/api/documents/{document.id}/content"
    }


@router.post("/{process_id}/generate-report")
async def generate_process_report(
    request: Request,
    process_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Generate technical report PDF for a process."""
    org_id = get_organization_from_token(request)
    
    # Get process
    process = db.query(Process).filter(
        Process.id == process_id,
        Process.organization_id == org_id
    ).first()
    
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process not found"
        )
    
    # Get checklist items
    checklist_items = db.query(ProcessChecklistItem).filter(
        ProcessChecklistItem.process_id == process_id
    ).all()
    
    # Get organization
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    
    # Calculate checklist stats
    total_items = len(checklist_items)
    completed_items = sum(1 for item in checklist_items if item.is_completed)
    pending_items = total_items - completed_items
    completion_rate = int((completed_items / total_items * 100)) if total_items > 0 else 0
    
    # Format status and priority for display
    status_map = {
        "EM_ANDAMENTO": "Em Andamento",
        "AGUARDANDO_ANALISE": "Aguardando Análise",
        "APROVADO": "Aprovado",
        "PENDENTE": "Pendente",
        "ATRASADO": "Atrasado",
        "CANCELADO": "Cancelado",
    }
    
    priority_map = {
        "BAIXA": "Baixa",
        "MEDIA": "Média",
        "ALTA": "Alta",
        "CRITICA": "Crítica",
    }
    
    # Prepare data dictionaries
    process_data = {
        'title': process.title,
        'protocol': process.protocol,
        'status': status_map.get(process.status.value, process.status.value),
        'priority': priority_map.get(process.priority.value, process.priority.value),
        'responsible': process.responsible or 'Não informado',
        'location': process.location or 'Não informado',
        'progress': process.progress or 0,
        'deadline': process.deadline.strftime('%d/%m/%Y') if process.deadline else 'Não informado',
        'summary': process.summary or 'Sem resumo disponível',
    }
    
    checklist_data = {
        'items': [{
            'title': item.title,
            'is_completed': item.is_completed,
            'order': item.order
        } for item in sorted(checklist_items, key=lambda x: x.order)],
        'total': total_items,
        'completed': completed_items,
        'pending': pending_items,
        'completion_rate': completion_rate,
    }
    
    user_data = {
        'full_name': current_user.full_name or 'Usuário',
        'email': current_user.email,
        'phone': current_user.phone or 'Não informado',
    }
    
    organization_data = {}
    if organization:
        organization_data = {
            'name': organization.name,
            'cnpj_cpf': organization.cnpj_cpf or 'N/A',
            'email': organization.email or 'N/A',
            'phone': organization.phone or 'N/A',
            'address': organization.address or 'N/A',
            'website': organization.website or 'N/A',
        }
    
    # Create reports directory if it doesn't exist
    reports_dir = os.path.join(os.getcwd(), "uploads", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    # Generate unique filename
    filename = f"parecer_tecnico_{process.protocol.replace('/', '-')}_{uuid.uuid4().hex[:8]}.pdf"
    output_path = os.path.join(reports_dir, filename)
    
    # Generate PDF
    try:
        generate_technical_report(
            process_data=process_data,
            checklist_data=checklist_data,
            user_data=user_data,
            organization_data=organization_data,
            output_path=output_path
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating report: {str(e)}"
        )
    
    # Log audit
    AuditLogger.log_create(
        db=db,
        entity_type="TechnicalReport",
        entity_id=process.id,
        user_id=current_user.id,
        organization_id=org_id,
        changes={"process_protocol": process.protocol, "filename": filename}
    )
    
    # Return file
    return FileResponse(
        path=output_path,
        media_type="application/pdf",
        filename=f"Parecer_Tecnico_{process.protocol.replace('/', '-')}.pdf"
    )
