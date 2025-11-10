'use client';

import React from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import {
  ArrowLeftIcon,
  UserIcon,
  BuildingOfficeIcon,
  CalendarIcon,
  DocumentTextIcon,
  PencilIcon,
  StopIcon,
} from '@heroicons/react/24/outline';

interface AssignmentDetails {
  id: number;
  employee_id: number;
  apartment_id: number;
  assignment_date: string;
  end_date: string | null;
  status: 'active' | 'ended';
  is_active: boolean;
  notes: string | null;
  employee: {
    id: number;
    hakenmoto_id: number;
    full_name_kanji: string;
    full_name_kana: string | null;
    phone: string | null;
    email: string | null;
  };
  apartment: {
    id: number;
    apartment_code: string;
    address: string;
    monthly_rent: number;
    capacity: number;
    employees_count: number;
  };
}

export default function AssignmentDetailsPage() {
  const router = useRouter();
  const params = useParams();
  const assignmentId = params.id as string;

  // Fetch assignment details
  const { data: assignment, isLoading, error } = useQuery({
    queryKey: ['apartment-assignment', assignmentId],
    queryFn: async () => {
      const response = await api.get(`/apartment-assignments/${assignmentId}`);
      return response.data as AssignmentDetails;
    },
  });

  // Status badge component
  const StatusBadge = ({ status, isActive }: { status: string; isActive: boolean }) => {
    const label = isActive ? 'Activa' : 'Finalizada';
    const style = isActive
      ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
      : 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400';

    return (
      <span className={`px-3 py-1 text-sm font-medium rounded-full ${style}`}>
        {label}
      </span>
    );
  };

  // Format date
  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="text-center py-12">Cargando asignación...</div>
      </div>
    );
  }

  if (error || !assignment) {
    return (
      <div className="p-6">
        <div className="text-center py-12 text-red-500">
          Error al cargar la asignación. Por favor, intenta de nuevo.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.back()}
            className="p-2 hover:bg-accent rounded-lg transition-colors"
          >
            <ArrowLeftIcon className="h-5 w-5" />
          </button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold">Asignación #{assignment.id}</h1>
              <StatusBadge status={assignment.status} isActive={assignment.is_active} />
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              {assignment.employee.full_name_kanji} → {assignment.apartment.apartment_code}
            </p>
          </div>
        </div>

        {assignment.is_active && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => router.push(`/apartment-assignments/${assignmentId}/end`)}
              className="flex items-center gap-2 px-4 py-2 border rounded-lg hover:bg-accent transition-colors"
            >
              <StopIcon className="h-5 w-5" />
              Finalizar Asignación
            </button>
          </div>
        )}
      </div>

      {/* Main Information */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Employee Card */}
        <div className="bg-card border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Información del Empleado</h2>

          <div className="flex items-center gap-4 mb-6">
            <div className="h-16 w-16 bg-primary/10 rounded-full flex items-center justify-center">
              <UserIcon className="h-8 w-8 text-primary" />
            </div>
            <div>
              <h3 className="font-semibold text-lg">{assignment.employee.full_name_kanji}</h3>
              {assignment.employee.full_name_kana && (
                <p className="text-sm text-muted-foreground">{assignment.employee.full_name_kana}</p>
              )}
              <p className="text-sm text-muted-foreground">ID: {assignment.employee.hakenmoto_id}</p>
            </div>
          </div>

          <div className="space-y-3 text-sm">
            {assignment.employee.phone && (
              <div>
                <p className="text-muted-foreground">Teléfono</p>
                <p className="font-medium">{assignment.employee.phone}</p>
              </div>
            )}
            {assignment.employee.email && (
              <div>
                <p className="text-muted-foreground">Email</p>
                <p className="font-medium">{assignment.employee.email}</p>
              </div>
            )}
          </div>

          <button
            onClick={() => router.push(`/employees/${assignment.employee.id}`)}
            className="w-full mt-4 px-4 py-2 border rounded-lg hover:bg-accent transition-colors text-sm"
          >
            Ver Perfil Completo
          </button>
        </div>

        {/* Apartment Card */}
        <div className="bg-card border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Información del Apartamento</h2>

          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <BuildingOfficeIcon className="h-6 w-6 text-primary mt-1" />
              <div>
                <p className="text-sm text-muted-foreground">Código</p>
                <p className="font-medium">{assignment.apartment.apartment_code}</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <BuildingOfficeIcon className="h-6 w-6 text-primary mt-1" />
              <div>
                <p className="text-sm text-muted-foreground">Dirección</p>
                <p className="font-medium">{assignment.apartment.address}</p>
              </div>
            </div>

            <div className="pt-3 border-t space-y-3 text-sm">
              <div>
                <p className="text-muted-foreground">Renta Mensual</p>
                <p className="font-medium text-lg">¥{assignment.apartment.monthly_rent.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Ocupación</p>
                <p className="font-medium">
                  {assignment.apartment.employees_count}/{assignment.apartment.capacity} personas
                </p>
              </div>
            </div>
          </div>

          <button
            onClick={() => router.push(`/apartments/${assignment.apartment.id}`)}
            className="w-full mt-4 px-4 py-2 border rounded-lg hover:bg-accent transition-colors text-sm"
          >
            Ver Apartamento
          </button>
        </div>

        {/* Assignment Details Card */}
        <div className="bg-card border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Detalles de la Asignación</h2>

          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <CalendarIcon className="h-6 w-6 text-primary mt-1" />
              <div>
                <p className="text-sm text-muted-foreground">Fecha de Inicio</p>
                <p className="font-medium">{formatDate(assignment.assignment_date)}</p>
              </div>
            </div>

            {assignment.end_date && (
              <div className="flex items-start gap-3">
                <CalendarIcon className="h-6 w-6 text-primary mt-1" />
                <div>
                  <p className="text-sm text-muted-foreground">Fecha de Finalización</p>
                  <p className="font-medium">{formatDate(assignment.end_date)}</p>
                </div>
              </div>
            )}

            {!assignment.end_date && (
              <div className="pt-4 border-t">
                <p className="text-sm text-muted-foreground mb-2">Duración</p>
                <p className="font-medium text-lg">
                  {Math.floor(
                    (new Date().getTime() - new Date(assignment.assignment_date).getTime()) /
                      (1000 * 60 * 60 * 24)
                  )}{' '}
                  días
                </p>
              </div>
            )}

            {assignment.notes && (
              <div className="pt-4 border-t">
                <p className="text-sm text-muted-foreground mb-2">Notas</p>
                <p className="text-sm">{assignment.notes}</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div className="bg-card border rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Historial</h2>
        <div className="space-y-4">
          <div className="flex items-start gap-4">
            <div className="h-10 w-10 bg-green-100 rounded-full flex items-center justify-center">
              <CalendarIcon className="h-5 w-5 text-green-600" />
            </div>
            <div className="flex-1">
              <p className="font-medium">Asignación creada</p>
              <p className="text-sm text-muted-foreground">
                {formatDate(assignment.assignment_date)}
              </p>
            </div>
          </div>

          {assignment.end_date && (
            <div className="flex items-start gap-4">
              <div className="h-10 w-10 bg-gray-100 rounded-full flex items-center justify-center">
                <CalendarIcon className="h-5 w-5 text-gray-600" />
              </div>
              <div className="flex-1">
                <p className="font-medium">Asignación finalizada</p>
                <p className="text-sm text-muted-foreground">
                  {formatDate(assignment.end_date)}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
