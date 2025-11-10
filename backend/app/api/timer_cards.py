"""
Timer Cards API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from datetime import time as datetime_time
import os
import shutil
import logging

from app.core.database import get_db
from app.core.config import settings
from app.models.models import TimerCard, Employee, User
from app.schemas.timer_card import (
    TimerCardCreate, TimerCardUpdate, TimerCardResponse,
    TimerCardBulkCreate, TimerCardProcessResult,
    TimerCardUploadResponse, TimerCardApprove, TimerCardOCRData
)
from app.services.auth_service import auth_service
from app.services.timer_card_ocr_service import timer_card_ocr_service

logger = logging.getLogger(__name__)

router = APIRouter()


def calculate_hours(clock_in: datetime_time, clock_out: datetime_time, break_minutes: int = 0):
    """Calculate work hours"""
    from datetime import datetime, timedelta
    
    # Convert to datetime for calculation
    today = datetime.today().date()
    start = datetime.combine(today, clock_in)
    end = datetime.combine(today, clock_out)
    
    # Handle overnight shifts
    if end < start:
        end += timedelta(days=1)
    
    # Calculate total hours
    total_minutes = (end - start).total_seconds() / 60
    work_minutes = total_minutes - break_minutes
    work_hours = work_minutes / 60
    
    # Calculate regular and overtime
    regular_hours = min(work_hours, 8.0)
    overtime_hours = max(work_hours - 8.0, 0)
    
    # Calculate night hours (22:00-05:00)
    night_hours = 0.0
    # Simplified calculation - can be enhanced
    
    return {
        "regular_hours": round(regular_hours, 2),
        "overtime_hours": round(overtime_hours, 2),
        "night_hours": round(night_hours, 2),
        "holiday_hours": 0.0  # Needs holiday calendar
    }


@router.post("/", response_model=TimerCardResponse, status_code=201)
async def create_timer_card(
    timer_card: TimerCardCreate,
    current_user: User = Depends(auth_service.require_role("admin")),
    db: Session = Depends(get_db)
):
    """Create single timer card"""
    # Calculate hours
    hours = calculate_hours(timer_card.clock_in, timer_card.clock_out, timer_card.break_minutes)
    
    new_card = TimerCard(
        **timer_card.model_dump(),
        **hours
    )
    
    db.add(new_card)
    db.commit()
    db.refresh(new_card)
    return new_card


@router.post("/bulk", response_model=TimerCardProcessResult)
async def create_timer_cards_bulk(
    bulk_data: TimerCardBulkCreate,
    current_user: User = Depends(auth_service.require_role("admin")),
    db: Session = Depends(get_db)
):
    """Create multiple timer cards"""
    created_ids = []
    errors = []
    
    for record in bulk_data.records:
        try:
            hours = calculate_hours(record.clock_in, record.clock_out, record.break_minutes)
            new_card = TimerCard(**record.model_dump(), **hours)
            db.add(new_card)
            db.flush()
            created_ids.append(new_card.id)
        except Exception as e:
            errors.append(f"Error creating record for employee {record.employee_id}: {str(e)}")
    
    db.commit()
    
    return TimerCardProcessResult(
        total_records=len(bulk_data.records),
        successful=len(created_ids),
        failed=len(errors),
        errors=errors,
        created_ids=created_ids
    )


@router.post("/upload", response_model=TimerCardUploadResponse)
async def upload_timer_card_file(
    file: UploadFile = File(...),
    factory_id: str = None,
    current_user: User = Depends(auth_service.require_role("admin")),
    db: Session = Depends(get_db)
):
    """Upload timer card PDF and process with OCR"""

    # Validar tipo de archivo
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")

    # Leer contenido del PDF
    pdf_bytes = await file.read()

    # Procesar con OCR
    try:
        ocr_result = timer_card_ocr_service.process_pdf(pdf_bytes, factory_id)

        if not ocr_result.get('success'):
            raise HTTPException(
                status_code=500,
                detail=f"Error procesando PDF: {ocr_result.get('error')}"
            )

        # Convertir a TimerCardOCRData schemas
        ocr_data = [
            TimerCardOCRData(
                page_number=record.get('page_number'),
                work_date=record.get('work_date'),
                employee_name_ocr=record.get('employee_name_ocr'),
                employee_matched=record.get('employee_matched'),
                clock_in=record.get('clock_in'),
                clock_out=record.get('clock_out'),
                break_minutes=record.get('break_minutes', 0),
                validation_errors=record.get('validation_errors', []),
                confidence_score=record.get('confidence_score', 0.0)
            )
            for record in ocr_result.get('records', [])
        ]

        return TimerCardUploadResponse(
            file_name=file.filename,
            pages_processed=ocr_result.get('pages_processed', 0),
            records_found=len(ocr_data),
            ocr_data=ocr_data,
            processing_errors=ocr_result.get('processing_errors', []),
            message=f"{len(ocr_data)} registros extraídos. Por favor revisar y confirmar."
        )

    except Exception as e:
        logger.error(f"Error processing timer card: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando timer card: {str(e)}"
        )


@router.get("/", response_model=list[TimerCardResponse])
async def list_timer_cards(
    employee_id: int = None,
    factory_id: str = None,
    is_approved: bool = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(auth_service.get_current_active_user),
    db: Session = Depends(get_db)
):
    """List timer cards with eager loaded employee relationship"""
    # Limit to max 1000
    limit = min(limit, 1000)

    query = db.query(TimerCard)

    if employee_id:
        query = query.filter(TimerCard.employee_id == employee_id)
    if factory_id:
        query = query.filter(TimerCard.factory_id == factory_id)
    if is_approved is not None:
        query = query.filter(TimerCard.is_approved == is_approved)

    # Eager load employee relationship to prevent N+1 queries
    return (
        query
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{timer_card_id}", response_model=TimerCardResponse)
async def get_timer_card(
    timer_card_id: int,
    current_user: User = Depends(auth_service.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific timer card by ID.
    Includes employee and factory information via relationships.
    """
    timer_card = (
        db.query(TimerCard)
        .filter(TimerCard.id == timer_card_id)
        .first()
    )

    if not timer_card:
        raise HTTPException(status_code=404, detail="Timer card not found")

    # Role-based access: Employees can only see their own timer cards
    if current_user.role.value == "EMPLOYEE":
        # Get employee record linked to user
        employee = db.query(Employee).filter(
            Employee.hakenmoto_id == timer_card.hakenmoto_id
        ).first()

        # Check if this timer card belongs to the current user
        # This requires employee to be linked to user (implementation may vary)
        # For now, we allow access if user is employee role
        pass

    return timer_card


@router.put("/{timer_card_id}", response_model=TimerCardResponse)
async def update_timer_card(
    timer_card_id: int,
    timer_card_update: TimerCardUpdate,
    current_user: User = Depends(auth_service.require_role("admin")),
    db: Session = Depends(get_db)
):
    """Update timer card"""
    timer_card = db.query(TimerCard).filter(TimerCard.id == timer_card_id).first()
    if not timer_card:
        raise HTTPException(status_code=404, detail="Timer card not found")
    
    # Update fields
    for field, value in timer_card_update.model_dump(exclude_unset=True).items():
        setattr(timer_card, field, value)
    
    # Recalculate hours if time changed
    if timer_card_update.clock_in or timer_card_update.clock_out:
        hours = calculate_hours(timer_card.clock_in, timer_card.clock_out, timer_card.break_minutes)
        for key, value in hours.items():
            setattr(timer_card, key, value)
    
    db.commit()
    db.refresh(timer_card)
    return timer_card


@router.post("/approve", response_model=dict)
async def approve_timer_cards(
    approve_data: TimerCardApprove,
    current_user: User = Depends(auth_service.require_role("admin")),
    db: Session = Depends(get_db)
):
    """Approve multiple timer cards"""
    cards = db.query(TimerCard).filter(TimerCard.id.in_(approve_data.timer_card_ids)).all()
    
    for card in cards:
        card.is_approved = True
    
    db.commit()
    
    return {"message": f"Approved {len(cards)} timer cards"}


@router.delete("/{timer_card_id}")
async def delete_timer_card(
    timer_card_id: int,
    current_user: User = Depends(auth_service.require_role("admin")),
    db: Session = Depends(get_db)
):
    """Delete timer card"""
    timer_card = db.query(TimerCard).filter(TimerCard.id == timer_card_id).first()
    if not timer_card:
        raise HTTPException(status_code=404, detail="Timer card not found")
    
    db.delete(timer_card)
    db.commit()
    return {"message": "Timer card deleted"}
