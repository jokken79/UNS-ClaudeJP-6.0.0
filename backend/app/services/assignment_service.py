"""
Servicio de Asignaciones V2.0
=============================

Servicio para gestión de asignaciones empleado-apartamento (社宅) con:
- Crear/actualizar/finalizar asignaciones
- Cálculo de renta prorrateada
- Transferencias entre apartamentos
- Integración con cargos adicionales y deducciones

Autor: Sistema UNS-ClaudeJP
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from typing import List, Optional, Tuple
from datetime import datetime, date
import calendar
from decimal import Decimal

from app.models.models import (
    Apartment,
    Employee,
    User,
)
from app.schemas.apartment_v2 import (
    AssignmentCreate,
    AssignmentResponse,
    AssignmentUpdate,
    AssignmentListItem,
    TransferRequest,
    TransferResponse,
    ProratedCalculationRequest,
    ProratedCalculationResponse,
    TotalCalculationRequest,
    TotalCalculationResponse,
    AssignmentStatus,
)


class AssignmentService:
    """Servicio para operaciones de asignaciones"""

    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------------------------
    # GESTIÓN DE ASIGNACIONES
    # -------------------------------------------------------------------------

    async def create_assignment(
        self,
        assignment: AssignmentCreate,
        user_id: int,
    ) -> AssignmentResponse:
        """
        Crear nueva asignación empleado-apartamento

        Flujo completo:
        1. Validar apartamento existe y está activo
        2. Validar empleado existe y está activo
        3. Verificar que empleado no tiene otra asignación activa
        4. Calcular renta prorrateada si es necesario
        5. Calcular total a descontar
        6. Crear registro en apartment_assignments
        7. Actualizar empleado (apartment_id)
        8. Generar deducción (si es mes completo)

        Args:
            assignment: Datos de la asignación
            user_id: ID del usuario

        Returns:
            Asignación creada

        Raises:
            HTTPException: Si hay validaciones fallidas
        """
        from fastapi import HTTPException

        # 1. Validar apartamento
        apartment = self.db.query(Apartment).filter(
            and_(
                Apartment.id == assignment.apartment_id,
                Apartment.deleted_at.is_(None)
            )
        ).first()

        if not apartment:
            raise HTTPException(
                status_code=404,
                detail="Apartamento no encontrado"
            )

        if apartment.status != "active":
            raise HTTPException(
                status_code=400,
                detail="El apartamento no está activo"
            )

        # 2. Validar empleado
        employee = self.db.query(Employee).filter(
            and_(
                Employee.id == assignment.employee_id,
                Employee.deleted_at.is_(None)
            )
        ).first()

        if not employee:
            raise HTTPException(
                status_code=404,
                detail="Empleado no encontrado"
            )

        if not employee.is_active:
            raise HTTPException(
                status_code=400,
                detail="El empleado no está activo"
            )

        # 3. Verificar que empleado no tiene asignación activa
        existing_assignment = self.db.query(Employee).filter(
            and_(
                Employee.id == assignment.employee_id,
                Employee.apartment_id.isnot(None),
                Employee.deleted_at.is_(None)
            )
        ).first()

        if existing_assignment:
            raise HTTPException(
                status_code=400,
                detail="El empleado ya tiene una asignación activa. Debe finalizarla primero."
            )

        # 4. Calcular renta prorrateada si es necesario
        prorated_rent = await self._calculate_rent_for_assignment(
            assignment.monthly_rent,
            assignment.start_date,
            assignment.end_date,
            assignment.year if hasattr(assignment, 'year') else assignment.start_date.year,
            assignment.month if hasattr(assignment, 'month') else assignment.start_date.month,
        )

        # 5. Calcular total a descontar (solo renta por ahora)
        total_deduction = prorated_rent.prorated_rent

        # 6. Crear asignación (placeholder - requiere tabla apartment_assignments)
        # TODO: Crear registro en apartment_assignments
        # assignment_record = ApartmentAssignment(...)

        # 7. Actualizar empleado
        employee.apartment_id = assignment.apartment_id
        employee.apartment_start_date = assignment.start_date
        employee.apartment_rent = assignment.monthly_rent
        employee.updated_at = datetime.now()

        # 8. Generar deducción si es mes completo
        if not prorated_rent.is_prorated:
            # TODO: Crear deducción en rent_deductions
            pass

        self.db.commit()

        # Construir respuesta
        return await self._build_assignment_response(
            assignment_id=1,  # Placeholder
            assignment_data=assignment,
            employee_data=employee,
            apartment_data=apartment,
            prorated_rent=prorated_rent,
        )

    async def end_assignment(
        self,
        assignment_id: int,
        update: AssignmentUpdate,
        user_id: int,
    ) -> AssignmentResponse:
        """
        Finalizar asignación (salida del empleado)

        Proceso:
        1. Validar asignación existe y está activa
        2. Calcular días ocupados hasta fecha fin
        3. Calcular renta prorrateada
        4. Agregar cargo de limpieza
        5. Agregar otros cargos adicionales
        6. Calcular total a descontar
        7. Actualizar asignación como 'ended'
        8. Actualizar empleado (apartment_id = null)
        9. Generar deducción final

        Args:
            assignment_id: ID de la asignación
            update: Datos de actualización
            user_id: ID del usuario

        Returns:
            Asignación finalizada

        Raises:
            HTTPException: Si hay validaciones fallidas
        """
        from fastapi import HTTPException

        # TODO: Obtener asignación desde apartment_assignments
        # assignment = self.db.query(ApartmentAssignment).filter(...)
        # if not assignment or assignment.status != AssignmentStatus.ACTIVE:

        # Placeholder para ejemplo
        raise HTTPException(status_code=501, detail="Funcionalidad en desarrollo")

    async def transfer_assignment(
        self,
        transfer: TransferRequest,
        user_id: int,
    ) -> TransferResponse:
        """
        Transferir empleado de un apartamento a otro (mudanza)

        Proceso atómico (3 pasos):
        1. Finalizar apartamento actual
        2. Iniciar nuevo apartamento
        3. Actualizar empleado

        Args:
            transfer: Datos de la transferencia
            user_id: ID del usuario

        Returns:
            Detalles de la transferencia

        Raises:
            HTTPException: Si hay validaciones fallidas
        """
        from fastapi import HTTPException
        from sqlalchemy.exc import SQLAlchemyError

        # TODO: Implementar transferencia completa
        # Placeholder para ejemplo
        raise HTTPException(status_code=501, detail="Funcionalidad en desarrollo")

    # -------------------------------------------------------------------------
    # LISTADO Y CONSULTA
    # -------------------------------------------------------------------------

    async def list_assignments(
        self,
        skip: int = 0,
        limit: int = 100,
        employee_id: Optional[int] = None,
        apartment_id: Optional[int] = None,
        status_filter: Optional[str] = None,
        start_date_from: Optional[date] = None,
        start_date_to: Optional[date] = None,
    ) -> List[AssignmentListItem]:
        """
        Listar asignaciones con filtros

        Args:
            skip: Registros a omitir
            limit: Límite de registros
            employee_id: Filtrar por empleado
            apartment_id: Filtrar por apartamento
            status_filter: Filtrar por estado
            start_date_from: Fecha inicio desde
            start_date_to: Fecha inicio hasta

        Returns:
            Lista de asignaciones
        """
        # TODO: Implementar consulta a apartment_assignments
        # Placeholder
        return []

    async def get_assignment(
        self,
        assignment_id: int,
    ) -> AssignmentResponse:
        """
        Obtener asignación por ID

        Args:
            assignment_id: ID de la asignación

        Returns:
            Asignación con detalles

        Raises:
            HTTPException: Si no se encuentra
        """
        from fastapi import HTTPException

        # TODO: Implementar consulta a apartment_assignments
        # Placeholder
        raise HTTPException(status_code=501, detail="Funcionalidad en desarrollo")

    async def get_active_assignments(
        self,
    ) -> List[AssignmentListItem]:
        """
        Obtener todas las asignaciones activas

        Returns:
            Lista de asignaciones activas
        """
        # TODO: Implementar
        return []

    # -------------------------------------------------------------------------
    # CÁLCULOS
    # -------------------------------------------------------------------------

    async def calculate_prorated_rent(
        self,
        calculation: ProratedCalculationRequest,
    ) -> ProratedCalculationResponse:
        """
        Calcular renta prorrateada

        Args:
            calculation: Datos para el cálculo

        Returns:
            Resultado del cálculo
        """
        # Calcular días en el mes
        days_in_month = calendar.monthrange(calculation.year, calculation.month)[1]

        # Calcular días ocupados
        if calculation.end_date:
            days_occupied = (calculation.end_date - calculation.start_date).days + 1
        else:
            # Hasta fin de mes
            end_of_month = datetime(calculation.year, calculation.month, days_in_month).date()
            days_occupied = (end_of_month - calculation.start_date).days + 1

        # Validar
        if days_occupied < 1:
            days_occupied = 1
        if days_occupied > days_in_month:
            days_occupied = days_in_month

        # Calcular tasa diaria (con decimales)
        daily_rate = Decimal(calculation.monthly_rent) / Decimal(days_in_month)

        # Calcular renta prorrateada y redondear
        prorated_rent = int((daily_rate * Decimal(days_occupied)).quantize(Decimal('1')))

        is_prorated = days_occupied != days_in_month

        return ProratedCalculationResponse(
            monthly_rent=calculation.monthly_rent,
            year=calculation.year,
            month=calculation.month,
            days_in_month=days_in_month,
            start_date=calculation.start_date,
            end_date=calculation.end_date,
            days_occupied=days_occupied,
            daily_rate=daily_rate,
            prorated_rent=prorated_rent,
            is_prorated=is_prorated,
        )

    async def calculate_total_deduction(
        self,
        calculation: TotalCalculationRequest,
    ) -> TotalCalculationResponse:
        """
        Calcular deducción total (renta + cargos adicionales)

        Fórmula:
        Total = Renta + Σ(Cargos Adicionales)

        Args:
            calculation: Datos para el cálculo

        Returns:
            Resultado del cálculo
        """
        # Sumar cargos adicionales
        additional_charges_total = sum(
            charge.get("amount", 0)
            for charge in calculation.additional_charges
        )

        # Calcular total
        total_deduction = calculation.base_rent + additional_charges_total

        # Construir breakdown
        breakdown = [
            {
                "type": "rent",
                "amount": calculation.base_rent,
                "description": "Renta prorrateada" if calculation.is_prorated else "Renta mensual"
            }
        ]

        for charge in calculation.additional_charges:
            breakdown.append({
                "type": charge.get("charge_type", "other"),
                "amount": charge.get("amount", 0),
                "description": charge.get("description", "Cargo adicional")
            })

        return TotalCalculationResponse(
            base_rent=calculation.base_rent,
            additional_charges_total=additional_charges_total,
            total_deduction=total_deduction,
            breakdown=breakdown,
        )

    # -------------------------------------------------------------------------
    # MÉTODOS AUXILIARES
    # -------------------------------------------------------------------------

    async def _calculate_rent_for_assignment(
        self,
        monthly_rent: int,
        start_date: date,
        end_date: Optional[date],
        year: int,
        month: int,
    ) -> ProratedCalculationResponse:
        """Calcular renta para una asignación"""
        # Crear request de cálculo
        calculation = ProratedCalculationRequest(
            monthly_rent=monthly_rent,
            start_date=start_date,
            end_date=end_date,
            year=year,
            month=month,
        )

        return await self.calculate_prorated_rent(calculation)

    async def _build_assignment_response(
        self,
        assignment_id: int,
        assignment_data: AssignmentCreate,
        employee_data: Employee,
        apartment_data: Apartment,
        prorated_rent: ProratedCalculationResponse,
    ) -> AssignmentResponse:
        """Construir respuesta de asignación"""
        # Placeholder - TODO: Implementar con datos reales
        return AssignmentResponse(
            id=assignment_id,
            apartment_id=assignment_data.apartment_id,
            employee_id=assignment_data.employee_id,
            start_date=assignment_data.start_date,
            end_date=assignment_data.end_date,
            monthly_rent=assignment_data.monthly_rent,
            days_in_month=prorated_rent.days_in_month,
            days_occupied=prorated_rent.days_occupied,
            prorated_rent=prorated_rent.prorated_rent,
            is_prorated=prorated_rent.is_prorated,
            total_deduction=prorated_rent.prorated_rent,
            contract_type=assignment_data.contract_type,
            notes=assignment_data.notes,
            status=AssignmentStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            apartment=ApartmentResponse(
                id=apartment_data.id,
                name=apartment_data.name,
                building_name=apartment_data.building_name,
                room_number=apartment_data.room_number,
                floor_number=apartment_data.floor_number,
                postal_code=apartment_data.postal_code,
                prefecture=apartment_data.prefecture,
                city=apartment_data.city,
                address_line1=apartment_data.address_line1,
                address_line2=apartment_data.address_line2,
                room_type=apartment_data.room_type,
                size_sqm=apartment_data.size_sqm,
                base_rent=apartment_data.base_rent,
                management_fee=apartment_data.management_fee,
                deposit=apartment_data.deposit,
                key_money=apartment_data.key_money,
                default_cleaning_fee=apartment_data.default_cleaning_fee,
                contract_start_date=apartment_data.contract_start_date,
                contract_end_date=apartment_data.contract_end_date,
                landlord_name=apartment_data.landlord_name,
                landlord_contact=apartment_data.landlord_contact,
                real_estate_agency=apartment_data.real_estate_agency,
                emergency_contact=apartment_data.emergency_contact,
                notes=apartment_data.notes,
                status=apartment_data.status,
                created_at=apartment_data.created_at,
                updated_at=apartment_data.updated_at,
                full_address=None,
                total_monthly_cost=apartment_data.base_rent + apartment_data.management_fee,
                active_assignments=0,
            ),
            employee={
                "id": employee_data.id,
                "full_name_kanji": employee_data.full_name_kanji,
                "full_name_kana": employee_data.full_name_kana,
            },
        )
