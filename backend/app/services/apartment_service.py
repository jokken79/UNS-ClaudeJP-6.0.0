"""
Servicio de Apartamentos V2.0
=============================

Servicio para la gestión de apartamentos (社宅) con:
- CRUD de apartamentos
- Búsqueda avanzada
- Cálculo de costos
- Gestión de cargos de limpieza
- Reportes de ocupación

Autor: Sistema UNS-ClaudeJP
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from typing import List, Optional, Tuple
from datetime import datetime
import calendar

from app.models.models import Apartment, User
from app.schemas.apartment_v2 import (
    ApartmentCreate,
    ApartmentUpdate,
    ApartmentResponse,
    ApartmentWithStats,
    CleaningFeeRequest,
    CleaningFeeResponse,
    ProratedCalculationRequest,
    ProratedCalculationResponse,
    RoomType,
)


class ApartmentService:
    """Servicio para operaciones de apartamentos"""

    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------------------------
    # CRUD APARTAMENTOS
    # -------------------------------------------------------------------------

    async def list_apartments(
        self,
        skip: int = 0,
        limit: int = 100,
        available_only: bool = False,
        search: Optional[str] = None,
        min_rent: Optional[int] = None,
        max_rent: Optional[int] = None,
        prefecture: Optional[str] = None,
    ) -> List[ApartmentResponse]:
        """
        Listar apartamentos con filtros opcionales

        Args:
            skip: Número de registros a omitir
            limit: Número máximo de registros
            available_only: Filtrar solo disponibles
            search: Búsqueda por texto
            min_rent: Renta mínima
            max_rent: Renta máxima
            prefecture: Prefecutura

        Returns:
            Lista de apartamentos con información básica
        """
        query = self.db.query(Apartment).filter(
            Apartment.deleted_at.is_(None)
        )

        # Aplicar filtros
        if available_only:
            query = query.filter(Apartment.status == "active")

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Apartment.name.ilike(search_pattern),
                    Apartment.building_name.ilike(search_pattern),
                    Apartment.city.ilike(search_pattern),
                    Apartment.address_line1.ilike(search_pattern),
                    Apartment.address_line2.ilike(search_pattern),
                )
            )

        if min_rent is not None:
            query = query.filter(Apartment.base_rent >= min_rent)

        if max_rent is not None:
            query = query.filter(Apartment.base_rent <= max_rent)

        if prefecture:
            query = query.filter(Apartment.prefecture == prefecture)

        # Ordenar por nombre
        query = query.order_by(Apartment.name)

        # Ejecutar query
        apartments = query.offset(skip).limit(limit).all()

        # Construir respuesta
        results = []
        for apt in apartments:
            # Calcular campos adicionales
            full_address = self._build_full_address(apt)
            total_monthly_cost = apt.base_rent + apt.management_fee

            results.append(ApartmentResponse(
                id=apt.id,
                name=apt.name,
                building_name=apt.building_name,
                room_number=apt.room_number,
                floor_number=apt.floor_number,
                postal_code=apt.postal_code,
                prefecture=apt.prefecture,
                city=apt.city,
                address_line1=apt.address_line1,
                address_line2=apt.address_line2,
                room_type=apt.room_type,
                size_sqm=apt.size_sqm,
                base_rent=apt.base_rent,
                management_fee=apt.management_fee,
                deposit=apt.deposit,
                key_money=apt.key_money,
                default_cleaning_fee=apt.default_cleaning_fee,
                contract_start_date=apt.contract_start_date,
                contract_end_date=apt.contract_end_date,
                landlord_name=apt.landlord_name,
                landlord_contact=apt.landlord_contact,
                real_estate_agency=apt.real_estate_agency,
                emergency_contact=apt.emergency_contact,
                notes=apt.notes,
                status=apt.status,
                created_at=apt.created_at,
                updated_at=apt.updated_at,
                full_address=full_address,
                total_monthly_cost=total_monthly_cost,
                active_assignments=0  # TODO: Contar asignaciones activas
            ))

        return results

    async def create_apartment(
        self,
        apartment: ApartmentCreate,
        user_id: int,
    ) -> ApartmentResponse:
        """
        Crear nuevo apartamento

        Args:
            apartment: Datos del apartamento
            user_id: ID del usuario que crea

        Returns:
            Apartamento creado

        Raises:
            HTTPException: Si el código de apartamento ya existe
        """
        # Verificar que el nombre no existe
        existing = self.db.query(Apartment).filter(
            and_(
                Apartment.name == apartment.name,
                Apartment.deleted_at.is_(None)
            )
        ).first()

        if existing:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe un apartamento con el nombre '{apartment.name}'"
            )

        # Crear apartamento
        db_apartment = Apartment(
            **apartment.model_dump(),
            created_at=datetime.now(),
        )

        self.db.add(db_apartment)
        self.db.commit()
        self.db.refresh(db_apartment)

        return await self._build_apartment_response(db_apartment)

    async def get_apartment_with_stats(
        self,
        apartment_id: int,
    ) -> ApartmentWithStats:
        """
        Obtener apartamento con estadísticas detalladas

        Args:
            apartment_id: ID del apartamento

        Returns:
            Apartamento con estadísticas

        Raises:
            HTTPException: Si no se encuentra el apartamento
        """
        apartment = self.db.query(Apartment).filter(
            and_(
                Apartment.id == apartment_id,
                Apartment.deleted_at.is_(None)
            )
        ).first()

        if not apartment:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=404,
                detail="Apartamento no encontrado"
            )

        # Calcular estadísticas
        stats = await self._calculate_apartment_stats(apartment_id)

        # Construir respuesta
        response = await self._build_apartment_response(apartment)
        response.current_occupancy = stats["current_occupancy"]
        response.max_occupancy = stats["max_occupancy"]
        response.occupancy_rate = stats["occupancy_rate"]
        response.is_available = response.status == "active" and stats["current_occupancy"] < stats["max_occupancy"]
        response.last_assignment_date = stats["last_assignment_date"]
        response.average_stay_duration = stats["average_stay_duration"]

        return response

    async def update_apartment(
        self,
        apartment_id: int,
        apartment: ApartmentUpdate,
        user_id: int,
    ) -> ApartmentResponse:
        """
        Actualizar apartamento

        Args:
            apartment_id: ID del apartamento
            apartment: Datos actualizados
            user_id: ID del usuario que actualiza

        Returns:
            Apartamento actualizado

        Raises:
            HTTPException: Si no se encuentra el apartamento
        """
        db_apartment = self.db.query(Apartment).filter(
            and_(
                Apartment.id == apartment_id,
                Apartment.deleted_at.is_(None)
            )
        ).first()

        if not db_apartment:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=404,
                detail="Apartamento no encontrado"
            )

        # Actualizar campos
        update_data = apartment.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_apartment, field, value)

        db_apartment.updated_at = datetime.now()

        self.db.commit()
        self.db.refresh(db_apartment)

        return await self._build_apartment_response(db_apartment)

    async def delete_apartment(
        self,
        apartment_id: int,
        user_id: int,
    ) -> None:
        """
        Eliminar apartamento (soft delete si tiene asignaciones)

        Args:
            apartment_id: ID del apartamento
            user_id: ID del usuario que elimina

        Raises:
            HTTPException: Si no se encuentra o tiene dependencias
        """
        db_apartment = self.db.query(Apartment).filter(
            and_(
                Apartment.id == apartment_id,
                Apartment.deleted_at.is_(None)
            )
        ).first()

        if not db_apartment:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=404,
                detail="Apartamento no encontrado"
            )

        # TODO: Verificar si tiene asignaciones activas
        # TODO: Verificar si tiene deducciones pendientes

        # Soft delete
        db_apartment.deleted_at = datetime.now()
        db_apartment.status = "inactive"
        db_apartment.updated_at = datetime.now()

        self.db.commit()

    # -------------------------------------------------------------------------
    # BÚSQUEDA AVANZADA
    # -------------------------------------------------------------------------

    async def search_apartments(
        self,
        q: Optional[str] = None,
        capacity_min: Optional[int] = None,
        size_min: Optional[float] = None,
        room_types: Optional[List[str]] = None,
        prefectures: Optional[List[str]] = None,
        has_management_fee: Optional[bool] = None,
        max_total_cost: Optional[int] = None,
        is_available: Optional[bool] = None,
        sort_by: str = "name",
        sort_order: str = "asc",
    ) -> List[ApartmentResponse]:
        """
        Búsqueda avanzada de apartamentos

        Args:
            q: Búsqueda de texto libre
            capacity_min: Capacidad mínima
            size_min: Tamaño mínimo
            room_types: Tipos de habitación
            prefectures: Lista de prefecturas
            has_management_fee: Tiene gastos de administración
            max_total_cost: Costo total máximo
            is_available: Disponibilidad
            sort_by: Campo de ordenamiento
            sort_order: Dirección de ordenamiento

        Returns:
            Lista de apartamentos que coinciden
        """
        query = self.db.query(Apartment).filter(
            Apartment.deleted_at.is_(None)
        )

        # Filtros de texto
        if q:
            search_pattern = f"%{q}%"
            query = query.filter(
                or_(
                    Apartment.name.ilike(search_pattern),
                    Apartment.building_name.ilike(search_pattern),
                    Apartment.room_number.ilike(search_pattern),
                    Apartment.city.ilike(search_pattern),
                    Apartment.address_line1.ilike(search_pattern),
                    Apartment.address_line2.ilike(search_pattern),
                    Apartment.landlord_name.ilike(search_pattern),
                )
            )

        # Filtros numéricos
        if capacity_min is not None:
            # TODO: Agregar campo capacity a la tabla
            pass

        if size_min is not None:
            query = query.filter(Apartment.size_sqm >= size_min)

        if max_total_cost is not None:
            # Filtrar por costo total (renta + gastos)
            query = query.filter(
                (Apartment.base_rent + Apartment.management_fee) <= max_total_cost
            )

        # Filtros de enum
        if room_types:
            query = query.filter(Apartment.room_type.in_(room_types))

        if prefectures:
            query = query.filter(Apartment.prefecture.in_(prefectures))

        # Filtros booleanos
        if has_management_fee is not None:
            if has_management_fee:
                query = query.filter(Apartment.management_fee > 0)
            else:
                query = query.filter(Apartment.management_fee == 0)

        if is_available is not None:
            if is_available:
                query = query.filter(
                    and_(
                        Apartment.status == "active",
                        # TODO: Verificar capacidad disponible
                    )
                )
            else:
                query = query.filter(Apartment.status == "inactive")

        # Ordenamiento
        sort_field = getattr(Apartment, sort_by, Apartment.name)
        if sort_order == "desc":
            query = query.order_by(desc(sort_field))
        else:
            query = query.order_by(sort_field)

        # Ejecutar
        apartments = query.all()

        # Construir respuesta
        results = []
        for apt in apartments:
            results.append(await self._build_apartment_response(apt))

        return results

    # -------------------------------------------------------------------------
    # CÁLCULOS
    # -------------------------------------------------------------------------

    async def calculate_prorated_rent(
        self,
        calculation: ProratedCalculationRequest,
    ) -> ProratedCalculationResponse:
        """
        Calcular renta prorrateada

        Fórmula:
        - Días en mes: 28, 29, 30 o 31 (dependiendo del mes)
        - Días ocupados: end_date - start_date + 1 (o hasta fin de mes si no hay end_date)
        - Renta diaria: monthly_rent / días_en_mes
        - Renta prorrateada: renta_diaria * días_ocupados
        - Redondeo: Al yen más cercano

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

    async def get_cleaning_fee(
        self,
        apartment_id: int,
        custom_amount: Optional[int] = None,
    ) -> CleaningFeeResponse:
        """
        Obtener cargo de limpieza para un apartamento

        Args:
            apartment_id: ID del apartamento
            custom_amount: Monto personalizado (opcional)

        Returns:
            Información del cargo de limpieza
        """
        apartment = self.db.query(Apartment).filter(Apartment.id == apartment_id).first()

        if not apartment:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=404,
                detail="Apartamento no encontrado"
            )

        default_amount = apartment.default_cleaning_fee

        if custom_amount is not None:
            final_amount = custom_amount
            is_custom = True
        else:
            final_amount = default_amount
            is_custom = False

        return CleaningFeeResponse(
            apartment_id=apartment_id,
            default_amount=default_amount,
            custom_amount=custom_amount,
            final_amount=final_amount,
            is_custom=is_custom,
        )

    # -------------------------------------------------------------------------
    # MÉTODOS AUXILIARES
    # -------------------------------------------------------------------------

    def _build_full_address(self, apartment: Apartment) -> Optional[str]:
        """Construir dirección completa"""
        parts = []
        if apartment.postal_code:
            parts.append(apartment.postal_code)
        if apartment.prefecture:
            parts.append(apartment.prefecture)
        if apartment.city:
            parts.append(apartment.city)
        if apartment.address_line1:
            parts.append(apartment.address_line1)
        if apartment.address_line2:
            parts.append(apartment.address_line2)

        return " ".join(parts) if parts else None

    async def _build_apartment_response(self, apartment: Apartment) -> ApartmentResponse:
        """Construir respuesta de apartamento"""
        full_address = self._build_full_address(apartment)
        total_monthly_cost = apartment.base_rent + apartment.management_fee

        return ApartmentResponse(
            id=apartment.id,
            name=apartment.name,
            building_name=apartment.building_name,
            room_number=apartment.room_number,
            floor_number=apartment.floor_number,
            postal_code=apartment.postal_code,
            prefecture=apartment.prefecture,
            city=apartment.city,
            address_line1=apartment.address_line1,
            address_line2=apartment.address_line2,
            room_type=apartment.room_type,
            size_sqm=apartment.size_sqm,
            base_rent=apartment.base_rent,
            management_fee=apartment.management_fee,
            deposit=apartment.deposit,
            key_money=apartment.key_money,
            default_cleaning_fee=apartment.default_cleaning_fee,
            contract_start_date=apartment.contract_start_date,
            contract_end_date=apartment.contract_end_date,
            landlord_name=apartment.landlord_name,
            landlord_contact=apartment.landlord_contact,
            real_estate_agency=apartment.real_estate_agency,
            emergency_contact=apartment.emergency_contact,
            notes=apartment.notes,
            status=apartment.status,
            created_at=apartment.created_at,
            updated_at=apartment.updated_at,
            full_address=full_address,
            total_monthly_cost=total_monthly_cost,
            active_assignments=0,  # TODO: Implementar
        )

    async def _calculate_apartment_stats(self, apartment_id: int) -> dict:
        """Calcular estadísticas de un apartamento"""
        # TODO: Implementar cálculo de estadísticas
        return {
            "current_occupancy": 0,
            "max_occupancy": 1,
            "occupancy_rate": 0.0,
            "last_assignment_date": None,
            "average_stay_duration": None,
        }
