'use client';

import React from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api'; // Default axios instance
import {
  ArrowLeftIcon,
  PencilIcon,
  TrashIcon,
  BuildingOfficeIcon,
  MapPinIcon,
  CurrencyYenIcon,
  UserGroupIcon,
  CalendarIcon,
  PhoneIcon,
  UserIcon,
} from '@heroicons/react/24/outline';

interface EmployeeBasic {
  id: number;
  hakenmoto_id: number;
  full_name_kanji: string;
  full_name_kana: string | null;
  phone: string | null;
  apartment_start_date: string | null;
}

interface ApartmentDetails {
  id: number;
  apartment_code: string;
  address: string;
  monthly_rent: number;
  capacity: number;
  is_available: boolean;
  notes: string | null;
  created_at: string;
  employees_count: number;
  occupancy_rate: number;
  status: 'disponible' | 'parcial' | 'lleno';
  employees: EmployeeBasic[];
}

export default function ApartmentDetailsPage() {
  const router = useRouter();
  const params = useParams();
  const apartmentId = params.id as string;

  // Fetch apartment details
  const { data: apartment, isLoading, error } = useQuery({
    queryKey: ['apartment', apartmentId],
    queryFn: async () => {
      const response = await api.get(`/apartments/${apartmentId}`);
      return response.data as ApartmentDetails;
    },
  });

  // Status badge component
  const StatusBadge = ({ status }: { status: string }) => {
    const styles = {
      disponible: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
      parcial: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
      lleno: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
    };

    const labels = {
      disponible: 'Disponible',
      parcial: 'Parcial',
      lleno: 'Lleno',
    };

    return (
      <span className={`px-3 py-1 text-sm font-medium rounded-full ${styles[status as keyof typeof styles]}`}>
        {labels[status as keyof typeof labels]}
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
        <div className="text-center py-12">Cargando detalles del apartamento...</div>
      </div>
    );
  }

  if (error || !apartment) {
    return (
      <div className="p-6">
        <div className="text-center py-12 text-red-500">
          Error al cargar el apartamento. Por favor, intenta de nuevo.
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
            <h1 className="text-3xl font-bold">{apartment.apartment_code}</h1>
            <p className="text-sm text-muted-foreground mt-1">{apartment.address}</p>
          </div>
          <StatusBadge status={apartment.status} />
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => router.push(`/apartments/${apartmentId}/edit`)}
            className="flex items-center gap-2 px-4 py-2 border rounded-lg hover:bg-accent transition-colors"
          >
            <PencilIcon className="h-5 w-5" />
            Editar
          </button>
        </div>
      </div>

      {/* Main Information */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Details Card */}
        <div className="lg:col-span-2 bg-card border rounded-lg p-6 space-y-6">
          <h2 className="text-xl font-semibold">Información del Apartamento</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="flex items-start gap-3">
              <BuildingOfficeIcon className="h-6 w-6 text-primary mt-1" />
              <div>
                <p className="text-sm text-muted-foreground">Código</p>
                <p className="font-medium">{apartment.apartment_code}</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <MapPinIcon className="h-6 w-6 text-primary mt-1" />
              <div>
                <p className="text-sm text-muted-foreground">Dirección</p>
                <p className="font-medium">{apartment.address}</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <CurrencyYenIcon className="h-6 w-6 text-primary mt-1" />
              <div>
                <p className="text-sm text-muted-foreground">Renta Mensual</p>
                <p className="font-medium">¥{apartment.monthly_rent.toLocaleString()}</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <UserGroupIcon className="h-6 w-6 text-primary mt-1" />
              <div>
                <p className="text-sm text-muted-foreground">Capacidad</p>
                <p className="font-medium">{apartment.capacity} personas</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <CalendarIcon className="h-6 w-6 text-primary mt-1" />
              <div>
                <p className="text-sm text-muted-foreground">Fecha de Creación</p>
                <p className="font-medium">{formatDate(apartment.created_at)}</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <UserGroupIcon className="h-6 w-6 text-primary mt-1" />
              <div>
                <p className="text-sm text-muted-foreground">Empleados Asignados</p>
                <p className="font-medium">
                  {apartment.employees_count} de {apartment.capacity}
                </p>
              </div>
            </div>
          </div>

          {/* Notes */}
          {apartment.notes && (
            <div className="pt-4 border-t">
              <p className="text-sm text-muted-foreground mb-2">Notas</p>
              <p className="text-sm">{apartment.notes}</p>
            </div>
          )}
        </div>

        {/* Stats Card */}
        <div className="space-y-4">
          <div className="bg-card border rounded-lg p-6">
            <h3 className="font-semibold mb-4">Estadísticas</h3>

            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-muted-foreground">Ocupación</span>
                  <span className="text-sm font-medium">{apartment.occupancy_rate.toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      apartment.status === 'disponible'
                        ? 'bg-green-500'
                        : apartment.status === 'parcial'
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                    }`}
                    style={{ width: `${Math.min(apartment.occupancy_rate, 100)}%` }}
                  />
                </div>
              </div>

              <div className="pt-4 border-t">
                <p className="text-sm text-muted-foreground">Espacios Disponibles</p>
                <p className="text-2xl font-bold mt-1">
                  {apartment.capacity - apartment.employees_count}
                </p>
              </div>

              <div className="pt-4 border-t">
                <p className="text-sm text-muted-foreground">Renta por Persona</p>
                <p className="text-2xl font-bold mt-1">
                  ¥{Math.round(apartment.monthly_rent / apartment.capacity).toLocaleString()}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Employees List */}
      <div className="bg-card border rounded-lg">
        <div className="p-4 border-b flex items-center justify-between">
          <h2 className="font-semibold">
            Empleados Asignados ({apartment.employees.length})
          </h2>
          {apartment.employees_count < apartment.capacity && (
            <button
              onClick={() => router.push(`/apartments/${apartmentId}/assign`)}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors text-sm"
            >
              Asignar Empleado
            </button>
          )}
        </div>

        {apartment.employees.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            No hay empleados asignados a este apartamento.
          </div>
        ) : (
          <div className="divide-y">
            {apartment.employees.map((employee) => (
              <div
                key={employee.id}
                className="p-4 hover:bg-accent cursor-pointer transition-colors"
                onClick={() => router.push(`/employees/${employee.id}`)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="h-12 w-12 bg-primary/10 rounded-full flex items-center justify-center">
                      <UserIcon className="h-6 w-6 text-primary" />
                    </div>
                    <div>
                      <p className="font-medium">{employee.full_name_kanji}</p>
                      {employee.full_name_kana && (
                        <p className="text-sm text-muted-foreground">{employee.full_name_kana}</p>
                      )}
                      <div className="flex items-center gap-4 mt-1">
                        <span className="text-xs text-muted-foreground">
                          ID: {employee.hakenmoto_id}
                        </span>
                        {employee.phone && (
                          <span className="text-xs text-muted-foreground flex items-center gap-1">
                            <PhoneIcon className="h-3 w-3" />
                            {employee.phone}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {employee.apartment_start_date && (
                    <div className="text-right">
                      <p className="text-sm text-muted-foreground">Fecha de Entrada</p>
                      <p className="text-sm font-medium">{formatDate(employee.apartment_start_date)}</p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
