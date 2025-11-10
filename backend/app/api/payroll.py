"""
Payroll API Router - FastAPI endpoints
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.services.payroll_service import PayrollService
from app.services.payroll_integration_service import PayrollIntegrationService
from app.schemas.payroll import (
    PayrollRunCreate,
    PayrollRun,
    PayrollRunSummary,
    EmployeePayrollCreate,
    EmployeePayrollResult,
    BulkPayrollRequest,
    BulkPayrollResult,
    PayslipRequest,
    PayslipInfo,
    PayrollSettings,
    PayrollSettingsCreate,
    PayrollSettingsUpdate,
    PayrollApprovalRequest,
    PayrollApprovalResponse,
    PayrollSummary,
    SuccessResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/api/payroll", tags=["payroll"])

# Dependency to get PayrollService
def get_payroll_service(db: Session = Depends(get_db)) -> PayrollService:
    return PayrollService(db_session=db)

# Dependency to get PayrollIntegrationService
def get_payroll_integration_service(db: Session = Depends(get_db)) -> PayrollIntegrationService:
    return PayrollIntegrationService(db_session=db)


# ============================================================================
# Payroll Runs Endpoints
# ============================================================================

@router.post(
    "/runs",
    response_model=PayrollRun,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new payroll run",
    description="Creates a new payroll run for a specific pay period"
)
def create_payroll_run(
    payroll_data: PayrollRunCreate,
    service: PayrollService = Depends(get_payroll_service)
):
    """Create a new payroll run.

    Args:
        payroll_data: Payroll run data with pay period dates
        service: Payroll service instance

    Returns:
        Created payroll run

    Raises:
        HTTPException: If creation fails
    """
    try:
        result = service.create_payroll_run(
            pay_period_start=payroll_data.pay_period_start.isoformat(),
            pay_period_end=payroll_data.pay_period_end.isoformat(),
            created_by=payroll_data.created_by
        )

        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['error']
            )

        # TODO: Return actual PayrollRun object from database
        # For now, return a mock response
        return PayrollRun(
            id=result.get('payroll_run_id', 1),
            pay_period_start=payroll_data.pay_period_start,
            pay_period_end=payroll_data.pay_period_end,
            status=result['status'],
            total_employees=0,
            total_gross_amount=0,
            total_deductions=0,
            total_net_amount=0,
            created_by=payroll_data.created_by,
            created_at=datetime.fromisoformat(result['created_at']),
            updated_at=datetime.fromisoformat(result['created_at'])
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating payroll run: {str(e)}"
        )


@router.get(
    "/runs",
    response_model=List[PayrollRunSummary],
    summary="Get all payroll runs",
    description="Retrieves a list of all payroll runs with pagination"
)
def get_payroll_runs(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    service: PayrollService = Depends(get_payroll_service),
    db: Session = Depends(get_db)
):
    """Get all payroll runs with optional filtering and pagination.

    Args:
        skip: Number of items to skip
        limit: Maximum number of items to return
        status_filter: Optional status filter
        service: Payroll service instance
        db: Database session

    Returns:
        List of payroll run summaries

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        # TODO: Implement actual database query
        # For now, return empty list
        return []

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving payroll runs: {str(e)}"
        )


@router.get(
    "/runs/{payroll_run_id}",
    response_model=PayrollRun,
    summary="Get payroll run details",
    description="Retrieves detailed information about a specific payroll run"
)
def get_payroll_run(
    payroll_run_id: int,
    service: PayrollService = Depends(get_payroll_service),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific payroll run.

    Args:
        payroll_run_id: ID of the payroll run
        service: Payroll service instance
        db: Database session

    Returns:
        Payroll run details

    Raises:
        HTTPException: If payroll run not found or retrieval fails
    """
    try:
        # TODO: Implement actual database query
        # For now, raise not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payroll run {payroll_run_id} not found"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving payroll run: {str(e)}"
        )


@router.post(
    "/runs/{payroll_run_id}/calculate",
    response_model=BulkPayrollResult,
    summary="Calculate payroll for all employees",
    description="Calculates payroll for all employees in a payroll run"
)
def calculate_payroll_run(
    payroll_run_id: int,
    request: BulkPayrollRequest,
    service: PayrollService = Depends(get_payroll_service)
):
    """Calculate payroll for all employees in a payroll run.

    Args:
        payroll_run_id: ID of the payroll run
        request: Bulk payroll request with employee data
        service: Payroll service instance

    Returns:
        Bulk payroll calculation results

    Raises:
        HTTPException: If calculation fails
    """
    try:
        result = service.calculate_bulk_payroll(
            employees_data=request.employees_data,
            payroll_run_id=payroll_run_id
        )

        if not result['total_employees']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No employee data provided"
            )

        return BulkPayrollResult(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating payroll: {str(e)}"
        )


@router.get(
    "/runs/{payroll_run_id}/employees",
    response_model=List[EmployeePayrollResult],
    summary="Get employees in payroll run",
    description="Retrieves all employees and their payroll calculations for a run"
)
def get_payroll_run_employees(
    payroll_run_id: int,
    service: PayrollService = Depends(get_payroll_service),
    db: Session = Depends(get_db)
):
    """Get all employees and their payroll calculations for a payroll run.

    Args:
        payroll_run_id: ID of the payroll run
        service: Payroll service instance
        db: Database session

    Returns:
        List of employee payroll results

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        # TODO: Implement actual database query
        # For now, return empty list
        return []

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving employees: {str(e)}"
        )


@router.post(
    "/runs/{payroll_run_id}/approve",
    response_model=PayrollApprovalResponse,
    summary="Approve a payroll run",
    description="Approves a payroll run for payment"
)
def approve_payroll_run(
    payroll_run_id: int,
    request: PayrollApprovalRequest,
    service: PayrollService = Depends(get_payroll_service),
    db: Session = Depends(get_db)
):
    """Approve a payroll run for payment.

    Args:
        payroll_run_id: ID of the payroll run
        request: Approval request with approver info
        service: Payroll service instance
        db: Database session

    Returns:
        Approval result

    Raises:
        HTTPException: If approval fails
    """
    try:
        # TODO: Implement actual database update
        # For now, return mock success
        return PayrollApprovalResponse(
            success=True,
            payroll_run_id=payroll_run_id,
            status="approved",
            approved_by=request.approved_by,
            approved_at=datetime.now()
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error approving payroll run: {str(e)}"
        )


# ============================================================================
# Employee Payroll Endpoints
# ============================================================================

@router.post(
    "/calculate",
    response_model=EmployeePayrollResult,
    summary="Calculate payroll for one employee",
    description="Calculates payroll for a single employee based on timer records"
)
def calculate_employee_payroll(
    request: EmployeePayrollCreate,
    service: PayrollService = Depends(get_payroll_service)
):
    """Calculate payroll for a single employee.

    Args:
        request: Employee payroll request with data and timer records
        service: Payroll service instance

    Returns:
        Employee payroll calculation result

    Raises:
        HTTPException: If calculation fails
    """
    try:
        result = service.calculate_employee_payroll(
            employee_data=request.employee_data.dict(),
            timer_records=[r.dict() for r in request.timer_records],
            payroll_run_id=request.payroll_run_id
        )

        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['error']
            )

        # Convert datetime strings to datetime objects
        if 'pay_period_start' in result:
            result['pay_period_start'] = result['pay_period_start']
        if 'pay_period_end' in result:
            result['pay_period_end'] = result['pay_period_end']

        return EmployeePayrollResult(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating payroll: {str(e)}"
        )


@router.post(
    "/calculate-from-timer-cards/{employee_id}",
    response_model=EmployeePayrollResult,
    summary="Calculate payroll from database timer cards",
    description="Calculates payroll for an employee using their timer card records from the database"
)
def calculate_payroll_from_timer_cards(
    employee_id: int = Path(..., ge=1, description="Employee ID"),
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    service: PayrollIntegrationService = Depends(get_payroll_integration_service)
):
    """Calculate payroll for an employee using their timer card records from the database.

    This endpoint:
    1. Fetches timer card records for the employee in the specified date range
    2. Matches timer cards to employee
    3. Calculates payroll based on the timer card data
    4. Returns the calculated payroll result

    Args:
        employee_id: Employee ID
        start_date: Start date in YYYY-MM-DD format (e.g., "2025-10-01")
        end_date: End date in YYYY-MM-DD format (e.g., "2025-10-31")
        service: Payroll integration service instance

    Returns:
        Employee payroll calculation result

    Raises:
        HTTPException: If employee not found or calculation fails
    """
    try:
        # Calculate payroll from timer cards
        result = service.calculate_payroll_from_timer_cards(
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date
        )

        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND if 'not found' in result.get('error', '').lower() else status.HTTP_400_BAD_REQUEST,
                detail=result['error']
            )

        return EmployeePayrollResult(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating payroll from timer cards: {str(e)}"
        )


# ============================================================================
# Payslip Endpoints
# ============================================================================

@router.post(
    "/payslips/generate",
    response_model=PayslipInfo,
    summary="Generate payslip PDF",
    description="Generates a payslip PDF for an employee"
)
def generate_payslip(
    request: PayslipRequest,
    service: PayrollService = Depends(get_payroll_service),
    db: Session = Depends(get_db)
):
    """Generate a payslip PDF for an employee.

    Args:
        request: Payslip generation request
        service: Payroll service instance
        db: Database session

    Returns:
        Payslip generation result

    Raises:
        HTTPException: If generation fails
    """
    try:
        # TODO: Get payroll data from database
        # For now, use mock data
        payroll_data = {
            'pay_period_start': '2025-10-01',
            'pay_period_end': '2025-10-31',
            'amounts': {
                'base_amount': 192000,
                'overtime_amount': 1500,
                'gross_amount': 200000,
                'total_deductions': 30000,
                'net_amount': 170000
            }
        }

        result = service.generate_payslip(
            employee_id=request.employee_id,
            payroll_data=payroll_data
        )

        return PayslipInfo(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating payslip: {str(e)}"
        )


@router.get(
    "/payslips/{payslip_id}",
    response_model=PayslipInfo,
    summary="Get payslip information",
    description="Retrieves information about a generated payslip"
)
def get_payslip(
    payslip_id: str,
    service: PayrollService = Depends(get_payroll_service)
):
    """Get information about a generated payslip.

    Args:
        payslip_id: ID of the payslip
        service: Payroll service instance

    Returns:
        Payslip information

    Raises:
        HTTPException: If payslip not found
    """
    try:
        result = service.payslip_generator.get_payslip_info(payslip_id)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payslip {payslip_id} not found"
            )

        return PayslipInfo(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving payslip: {str(e)}"
        )


# ============================================================================
# Payroll Settings Endpoints
# ============================================================================

@router.get(
    "/settings",
    response_model=PayrollSettings,
    summary="Get payroll settings",
    description="Retrieves the current payroll settings"
)
def get_payroll_settings(
    service: PayrollService = Depends(get_payroll_service),
    db: Session = Depends(get_db)
):
    """Get current payroll settings.

    Args:
        service: Payroll service instance
        db: Database session

    Returns:
        Payroll settings

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        settings = service._get_payroll_settings()

        if not settings:
            # Return default settings
            return PayrollSettings(
                id=1,
                company_id=None,
                overtime_rate=1.25,
                night_shift_rate=1.25,
                holiday_rate=1.35,
                sunday_rate=1.35,
                standard_hours_per_month=160,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

        # Convert Decimal to float for Pydantic
        settings_dict = {k: float(v) if isinstance(v, (int, float)) else v
                        for k, v in settings.items()}

        return PayrollSettings(
            id=1,
            company_id=settings_dict.get('company_id'),
            overtime_rate=settings_dict.get('overtime_rate', 1.25),
            night_shift_rate=settings_dict.get('night_shift_rate', 1.25),
            holiday_rate=settings_dict.get('holiday_rate', 1.35),
            sunday_rate=settings_dict.get('sunday_rate', 1.35),
            standard_hours_per_month=settings_dict.get('standard_hours_per_month', 160),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving settings: {str(e)}"
        )


@router.put(
    "/settings",
    response_model=PayrollSettings,
    summary="Update payroll settings",
    description="Updates the payroll settings"
)
def update_payroll_settings(
    settings: PayrollSettingsUpdate,
    service: PayrollService = Depends(get_payroll_service)
):
    """Update payroll settings.

    Args:
        settings: Updated settings data
        service: Payroll service instance

    Returns:
        Updated payroll settings

    Raises:
        HTTPException: If update fails
    """
    try:
        # Convert to dict, excluding None values
        settings_dict = {k: v for k, v in settings.dict(exclude_unset=True).items()
                        if v is not None}

        result = service.update_payroll_settings(settings_dict)

        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['error']
            )

        return PayrollSettings(
            id=1,
            company_id=None,
            **settings_dict,
            created_at=datetime.now(),
            updated_at=datetime.fromisoformat(result['updated_at'])
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating settings: {str(e)}"
        )


# ============================================================================
# Summary Endpoints
# ============================================================================

@router.get(
    "/summary",
    response_model=List[PayrollSummary],
    summary="Get payroll summary",
    description="Retrieves a summary view of all payroll runs"
)
def get_payroll_summary(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of items to return"),
    service: PayrollService = Depends(get_payroll_service),
    db: Session = Depends(get_db)
):
    """Get a summary view of all payroll runs.

    Args:
        skip: Number of items to skip
        limit: Maximum number of items to return
        service: Payroll service instance
        db: Database session

    Returns:
        List of payroll summaries

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        # TODO: Implement actual database query using vw_payroll_summary view
        # For now, return empty list
        return []

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving summary: {str(e)}"
        )
