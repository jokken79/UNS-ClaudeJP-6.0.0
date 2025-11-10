"""
Requests API Endpoints (Yukyu, Ikkikokoku, Taisha, etc.)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import date

from app.core.database import get_db
from app.models.models import Request, Employee, User, RequestType, RequestStatus
from app.schemas.request import RequestCreate, RequestUpdate, RequestResponse, RequestReview
from app.schemas.base import PaginatedResponse, create_paginated_response
from app.services.auth_service import auth_service

router = APIRouter()


@router.post("/", response_model=RequestResponse, status_code=201)
async def create_request(
    request_data: RequestCreate,
    current_user: User = Depends(auth_service.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create new request (yukyu, ikkikokoku, etc.)"""
    # Verify employee exists
    employee = db.query(Employee).filter(Employee.id == request_data.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Check if employee can make request (only their own unless admin)
    if current_user.role.value == "employee":
        # Employee can only request for themselves
        # You'd need to link user to employee here
        pass

    # Calculate total days (for validation)
    delta = request_data.end_date - request_data.start_date
    total_days = delta.days + 1

    # Check yukyu balance for yukyu/hankyu requests
    if request_data.request_type in [RequestType.YUKYU, RequestType.HANKYU]:
        if employee.yukyu_remaining < float(total_days):
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient yukyu balance. Available: {employee.yukyu_remaining}"
            )

    # Create request with hakenmoto_id from employee
    request_dict = request_data.model_dump()
    request_dict['hakenmoto_id'] = employee.hakenmoto_id
    del request_dict['employee_id']  # Remove employee_id from schema
    if 'total_days' in request_dict:
        del request_dict['total_days']  # Remove total_days - it's a computed property

    new_request = Request(**request_dict)
    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    return new_request


@router.get("/", response_model=PaginatedResponse[RequestResponse])
async def list_requests(
    employee_id: int = Query(None, description="Filter by employee ID"),
    status: RequestStatus = Query(None, description="Filter by request status"),
    request_type: RequestType = Query(None, description="Filter by request type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(auth_service.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List requests with pagination.

    Returns paginated list of employee requests (yukyu, ikkikokoku, taisha, etc.)
    """
    query = db.query(Request)

    # Apply filters
    if employee_id:
        # Convert employee.id to hakenmoto_id for filtering
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if employee:
            query = query.filter(Request.hakenmoto_id == employee.hakenmoto_id)
        else:
            # If employee not found, return empty result
            return create_paginated_response(items=[], total=0, page=page, page_size=page_size)

    if status:
        query = query.filter(Request.status == status)
    if request_type:
        query = query.filter(Request.request_type == request_type)

    # Get total count
    total = query.count()

    # Calculate pagination
    skip = (page - 1) * page_size

    # Get paginated results
    items = (
        query
        .order_by(Request.created_at.desc())
        .offset(skip)
        .limit(page_size)
        .all()
    )

    return create_paginated_response(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{request_id}", response_model=RequestResponse)
async def get_request(
    request_id: int,
    current_user: User = Depends(auth_service.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get request by ID"""
    request = db.query(Request).filter(Request.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    return request


@router.put("/{request_id}", response_model=RequestResponse)
async def update_request(
    request_id: int,
    request_update: RequestUpdate,
    current_user: User = Depends(auth_service.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update request (before approval)"""
    request = db.query(Request).filter(Request.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.status != RequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="Can only update pending requests")

    # Update fields, excluding total_days (computed property)
    for field, value in request_update.model_dump(exclude_unset=True).items():
        if field != 'total_days':
            setattr(request, field, value)

    db.commit()
    db.refresh(request)
    return request


@router.post("/{request_id}/review", response_model=RequestResponse)
async def review_request(
    request_id: int,
    review_data: RequestReview,
    current_user: User = Depends(auth_service.require_role("admin")),
    db: Session = Depends(get_db)
):
    """Approve or reject request"""
    request = db.query(Request).filter(Request.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.status != RequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="Request already reviewed")

    request.status = review_data.status
    request.approved_by = current_user.id
    request.approved_at = func.now()
    if review_data.notes:
        request.notes = review_data.notes

    # Update yukyu balance if approved
    if review_data.status == RequestStatus.APPROVED:
        if request.request_type in [RequestType.YUKYU, RequestType.HANKYU]:
            employee = db.query(Employee).filter(Employee.hakenmoto_id == request.hakenmoto_id).first()
            if employee:
                employee.yukyu_used += float(request.total_days)
                employee.yukyu_remaining -= float(request.total_days)

    db.commit()
    db.refresh(request)
    return request


@router.post("/{request_id}/approve", response_model=RequestResponse)
async def approve_request(
    request_id: int,
    current_user: User = Depends(auth_service.require_role("admin")),
    db: Session = Depends(get_db)
):
    """
    Approve a request (convenience endpoint).
    Shortcut for /review with status=APPROVED.
    """
    request = db.query(Request).filter(Request.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.status != RequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="Request already reviewed")

    request.status = RequestStatus.APPROVED
    request.approved_by = current_user.id
    request.approved_at = func.now()

    # Update yukyu balance if approved
    if request.request_type in [RequestType.YUKYU, RequestType.HANKYU]:
        employee = db.query(Employee).filter(Employee.hakenmoto_id == request.hakenmoto_id).first()
        if employee:
            employee.yukyu_used += float(request.total_days)
            employee.yukyu_remaining -= float(request.total_days)

    db.commit()
    db.refresh(request)
    return request


@router.post("/{request_id}/reject", response_model=RequestResponse)
async def reject_request_endpoint(
    request_id: int,
    reason: str,
    current_user: User = Depends(auth_service.require_role("admin")),
    db: Session = Depends(get_db)
):
    """
    Reject a request with reason (convenience endpoint).
    Shortcut for /review with status=REJECTED.
    """
    request = db.query(Request).filter(Request.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.status != RequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="Request already reviewed")

    request.status = RequestStatus.REJECTED
    request.approved_by = current_user.id
    request.approved_at = func.now()
    request.notes = reason

    db.commit()
    db.refresh(request)
    return request


@router.delete("/{request_id}")
async def delete_request(
    request_id: int,
    current_user: User = Depends(auth_service.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete request (only pending requests)"""
    request = db.query(Request).filter(Request.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.status != RequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="Can only delete pending requests")

    db.delete(request)
    db.commit()
    return {"message": "Request deleted"}
