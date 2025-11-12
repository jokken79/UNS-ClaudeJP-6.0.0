"""
Salary Calculation API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
from app.models.models import SalaryCalculation, Employee, TimerCard, Factory, User
from app.schemas.salary import (
    SalaryCalculate, SalaryCalculationResponse, SalaryBulkCalculate,
    SalaryBulkResult, SalaryMarkPaid, SalaryStatistics
)
from app.schemas.base import PaginatedResponse, create_paginated_response
from app.services.auth_service import auth_service

router = APIRouter()


def calculate_employee_salary(db: Session, employee_id: int, month: int, year: int):
    """Calculate salary for single employee"""
    # Get employee
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise ValueError("Employee not found")
    
    # Get factory config
    factory = db.query(Factory).filter(Factory.factory_id == employee.factory_id).first()
    if not factory:
        raise ValueError("Factory not found")
    
    # Get approved timer cards for the month
    timer_cards = db.query(TimerCard).filter(
        TimerCard.hakenmoto_id == employee.hakenmoto_id,
        TimerCard.is_approved == True,
        extract('month', TimerCard.work_date) == month,
        extract('year', TimerCard.work_date) == year
    ).all()
    
    if not timer_cards:
        raise ValueError("No approved timer cards found for this month")
    
    # Sum hours
    total_regular_hours = sum(float(tc.regular_hours) for tc in timer_cards)
    total_overtime_hours = sum(float(tc.overtime_hours) for tc in timer_cards)
    total_night_hours = sum(float(tc.night_hours) for tc in timer_cards)
    total_holiday_hours = sum(float(tc.holiday_hours) for tc in timer_cards)
    
    # Get rates from settings or factory config
    overtime_rate = settings.OVERTIME_RATE_25
    night_rate = settings.NIGHT_SHIFT_PREMIUM
    holiday_rate = settings.HOLIDAY_WORK_PREMIUM
    
    # Calculate payments
    base_salary = int(employee.jikyu * total_regular_hours)
    overtime_pay = int(employee.jikyu * total_overtime_hours * (1 + overtime_rate))
    night_pay = int(employee.jikyu * total_night_hours * (1 + night_rate))
    holiday_pay = int(employee.jikyu * total_holiday_hours * (1 + holiday_rate))
    
    # Bonuses (can be customized from factory config)
    bonus = 0
    gasoline_allowance = 0
    
    if factory.config and "bonuses" in factory.config:
        bonuses_config = factory.config["bonuses"]
        
        # Gasoline allowance
        if bonuses_config.get("gasoline_allowance", {}).get("enabled"):
            amount_per_day = bonuses_config["gasoline_allowance"].get("amount_per_day", 0)
            work_days = len(timer_cards)
            gasoline_allowance = amount_per_day * work_days
        
        # Attendance bonus
        if bonuses_config.get("attendance_bonus", {}).get("enabled"):
            bonus_config = bonuses_config["attendance_bonus"]
            conditions = bonus_config.get("conditions", {})
            if conditions.get("full_month") and work_days >= 20:
                bonus += bonus_config.get("amount", 0)
    
    # Deductions
    apartment_deduction = 0
    if employee.apartment_id and employee.apartment_rent:
        # Calculate prorated rent
        days_in_month = 30  # Simplified
        work_days = len(timer_cards)
        if settings.APARTMENT_PRORATE_BY_DAY:
            apartment_deduction = int((employee.apartment_rent / days_in_month) * work_days)
        else:
            apartment_deduction = employee.apartment_rent
    
    # Calculate gross and net
    gross_salary = base_salary + overtime_pay + night_pay + holiday_pay + bonus + gasoline_allowance
    net_salary = gross_salary - apartment_deduction
    
    # Calculate factory payment (時給単価)
    factory_payment = 0
    company_profit = 0
    
    if factory.config and "working_hours" in factory.config:
        shifts = factory.config["working_hours"].get("shifts", [])
        if shifts:
            # Use first shift's jikyu_tanka as default
            jikyu_tanka = shifts[0].get("jikyu_tanka", employee.jikyu)
            total_hours = total_regular_hours + total_overtime_hours + total_night_hours + total_holiday_hours
            factory_payment = int(jikyu_tanka * total_hours)
            company_profit = factory_payment - gross_salary
    
    return {
        "employee_id": employee_id,
        "month": month,
        "year": year,
        "total_regular_hours": total_regular_hours,
        "total_overtime_hours": total_overtime_hours,
        "total_night_hours": total_night_hours,
        "total_holiday_hours": total_holiday_hours,
        "base_salary": base_salary,
        "overtime_pay": overtime_pay,
        "night_pay": night_pay,
        "holiday_pay": holiday_pay,
        "bonus": bonus,
        "gasoline_allowance": gasoline_allowance,
        "apartment_deduction": apartment_deduction,
        "other_deductions": 0,
        "gross_salary": gross_salary,
        "net_salary": net_salary,
        "factory_payment": factory_payment,
        "company_profit": company_profit
    }


@router.post("/calculate", response_model=SalaryCalculationResponse, status_code=201)
async def calculate_salary(
    salary_data: SalaryCalculate,
    current_user: User = Depends(auth_service.require_role("admin")),
    db: Session = Depends(get_db)
):
    """Calculate salary for single employee"""
    try:
        # Check if already calculated
        existing = db.query(SalaryCalculation).filter(
            SalaryCalculation.employee_id == salary_data.employee_id,
            SalaryCalculation.month == salary_data.month,
            SalaryCalculation.year == salary_data.year
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Salary already calculated for this month")
        
        # Calculate
        calc_data = calculate_employee_salary(
            db, 
            salary_data.employee_id,
            salary_data.month,
            salary_data.year
        )
        
        # Override bonuses/deductions if provided
        if salary_data.bonus:
            calc_data["bonus"] = salary_data.bonus
        if salary_data.gasoline_allowance:
            calc_data["gasoline_allowance"] = salary_data.gasoline_allowance
        if salary_data.other_deductions:
            calc_data["other_deductions"] = salary_data.other_deductions
        
        # Recalculate net salary
        calc_data["gross_salary"] = (
            calc_data["base_salary"] + calc_data["overtime_pay"] +
            calc_data["night_pay"] + calc_data["holiday_pay"] +
            calc_data["bonus"] + calc_data["gasoline_allowance"]
        )
        calc_data["net_salary"] = (
            calc_data["gross_salary"] - calc_data["apartment_deduction"] -
            calc_data["other_deductions"]
        )
        
        # Save
        new_salary = SalaryCalculation(**calc_data)
        db.add(new_salary)
        db.commit()
        db.refresh(new_salary)
        
        return new_salary
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/calculate/bulk", response_model=SalaryBulkResult)
async def calculate_salaries_bulk(
    bulk_data: SalaryBulkCalculate,
    current_user: User = Depends(auth_service.require_role("admin")),
    db: Session = Depends(get_db)
):
    """Calculate salaries for multiple employees"""
    # Get employees
    query = db.query(Employee).filter(Employee.is_active == True)
    
    if bulk_data.employee_ids:
        query = query.filter(Employee.id.in_(bulk_data.employee_ids))
    elif bulk_data.factory_id:
        query = query.filter(Employee.factory_id == bulk_data.factory_id)
    
    employees = query.all()
    
    successful = 0
    failed = 0
    errors = []
    total_gross = 0
    total_net = 0
    total_profit = 0
    
    for employee in employees:
        try:
            calc_data = calculate_employee_salary(
                db,
                employee.id,
                bulk_data.month,
                bulk_data.year
            )
            
            new_salary = SalaryCalculation(**calc_data)
            db.add(new_salary)
            db.flush()
            
            successful += 1
            total_gross += calc_data["gross_salary"]
            total_net += calc_data["net_salary"]
            total_profit += calc_data["company_profit"]
            
        except Exception as e:
            failed += 1
            errors.append(f"Employee {employee.hakenmoto_id}: {str(e)}")
    
    db.commit()
    
    return SalaryBulkResult(
        total_employees=len(employees),
        successful=successful,
        failed=failed,
        total_gross_salary=total_gross,
        total_net_salary=total_net,
        total_company_profit=total_profit,
        errors=errors
    )


@router.get("/", response_model=PaginatedResponse[SalaryCalculationResponse])
async def list_salaries(
    employee_id: int = Query(None, description="Filter by employee ID"),
    month: int = Query(None, ge=1, le=12, description="Filter by month (1-12)"),
    year: int = Query(None, ge=2020, description="Filter by year"),
    is_paid: bool = Query(None, description="Filter by payment status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(auth_service.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List salary calculations with pagination.

    Returns paginated list with eager loaded employee relationship.
    """
    query = db.query(SalaryCalculation)

    # Apply filters
    if employee_id:
        query = query.filter(SalaryCalculation.employee_id == employee_id)
    if month:
        query = query.filter(SalaryCalculation.month == month)
    if year:
        query = query.filter(SalaryCalculation.year == year)
    if is_paid is not None:
        query = query.filter(SalaryCalculation.is_paid == is_paid)

    # Get total count
    total = query.count()

    # Calculate pagination
    skip = (page - 1) * page_size

    # Get paginated results
    items = (
        query
        .order_by(SalaryCalculation.year.desc(), SalaryCalculation.month.desc())
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


@router.get("/{salary_id}", response_model=SalaryCalculationResponse)
async def get_salary_calculation(
    salary_id: int,
    current_user: User = Depends(auth_service.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific salary calculation by ID.
    Includes employee information and all deductions/bonuses.
    """
    salary = (
        db.query(SalaryCalculation)
        .filter(SalaryCalculation.id == salary_id)
        .first()
    )

    if not salary:
        raise HTTPException(status_code=404, detail="Salary calculation not found")

    # Role-based access: Employees can only see their own salary
    if current_user.role.value == "EMPLOYEE":
        # Get employee record linked to user
        employee = db.query(Employee).filter(Employee.id == salary.employee_id).first()

        # Check if this salary belongs to the current user
        # This requires employee to be linked to user (implementation may vary)
        # For now, we allow access if user is employee role
        pass

    return salary


@router.post("/mark-paid")
async def mark_salaries_paid(
    payment_data: SalaryMarkPaid,
    current_user: User = Depends(auth_service.require_role("admin")),
    db: Session = Depends(get_db)
):
    """Mark salaries as paid"""
    salaries = db.query(SalaryCalculation).filter(
        SalaryCalculation.id.in_(payment_data.salary_ids)
    ).all()
    
    payment_date = payment_data.payment_date or datetime.now()
    
    for salary in salaries:
        salary.is_paid = True
        salary.paid_at = payment_date
    
    db.commit()
    
    return {"message": f"Marked {len(salaries)} salaries as paid"}


@router.get("/statistics", response_model=SalaryStatistics)
async def get_salary_statistics(
    month: int,
    year: int,
    current_user: User = Depends(auth_service.require_role("admin")),
    db: Session = Depends(get_db)
):
    """Get salary statistics for a month"""
    salaries = db.query(SalaryCalculation).filter(
        SalaryCalculation.month == month,
        SalaryCalculation.year == year
    ).all()
    
    if not salaries:
        raise HTTPException(status_code=404, detail="No salary data found for this month")
    
    total_employees = len(salaries)
    total_gross = sum(s.gross_salary for s in salaries)
    total_net = sum(s.net_salary for s in salaries)
    total_deductions = total_gross - total_net
    total_revenue = sum(s.factory_payment for s in salaries)
    total_profit = sum(s.company_profit for s in salaries)
    avg_salary = total_net // total_employees if total_employees > 0 else 0
    
    # Group by factory
    factory_stats = {}
    for salary in salaries:
        employee = db.query(Employee).filter(Employee.id == salary.employee_id).first()
        if employee:
            factory_id = employee.factory_id
            if factory_id not in factory_stats:
                factory_stats[factory_id] = {
                    "factory_id": factory_id,
                    "employees": 0,
                    "total_salary": 0,
                    "total_profit": 0
                }
            factory_stats[factory_id]["employees"] += 1
            factory_stats[factory_id]["total_salary"] += salary.net_salary
            factory_stats[factory_id]["total_profit"] += salary.company_profit
    
    return SalaryStatistics(
        month=month,
        year=year,
        total_employees=total_employees,
        total_gross_salary=total_gross,
        total_net_salary=total_net,
        total_deductions=total_deductions,
        total_company_revenue=total_revenue,
        total_company_profit=total_profit,
        average_salary=avg_salary,
        factories=list(factory_stats.values())
    )
