'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api'; // Default axios instance
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  PlusIcon,
  BuildingOfficeIcon,
  UserGroupIcon,
  ChartBarIcon,
  CurrencyYenIcon,
  XMarkIcon,
  PencilIcon,
  EyeIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';

// Apartment interface matching backend schema
interface Apartment {
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
}

interface ApartmentStats {
  total_apartments: number;
  total_capacity: number;
  apartments_occupied: number;
  apartments_available: number;
  apartments_full: number;
  total_employees_assigned: number;
  occupancy_percentage: number;
  total_monthly_rent: number;
  average_rent: number;
}

export default function ApartmentsPage() {
  const router = useRouter();
  const [search, setSearch] = useState('');
  const [availableOnly, setAvailableOnly] = useState(false);
  const [minCapacity, setMinCapacity] = useState<number | ''>('');
  const [maxRent, setMaxRent] = useState<number | ''>('');
  const [showFilters, setShowFilters] = useState(false);

  // Fetch apartments list
  const { data: apartments = [], isLoading: apartmentsLoading, error: apartmentsError } = useQuery({
    queryKey: ['apartments', { search, availableOnly, minCapacity, maxRent }],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (availableOnly) params.append('available_only', 'true');
      if (minCapacity) params.append('min_capacity', String(minCapacity));
      if (maxRent) params.append('max_rent', String(maxRent));

      const response = await api.get(`/apartments/?${params.toString()}`);
      return response.data as Apartment[];
    },
  });

  // Fetch statistics
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['apartments-stats'],
    queryFn: async () => {
      const response = await api.get('/apartments/stats');
      return response.data as ApartmentStats;
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
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${styles[status as keyof typeof styles]}`}>
        {labels[status as keyof typeof labels]}
      </span>
    );
  };

  // Clear all filters
  const clearFilters = () => {
    setSearch('');
    setAvailableOnly(false);
    setMinCapacity('');
    setMaxRent('');
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Gestión de Apartamentos</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Administra los apartamentos de la empresa
          </p>
        </div>
        <button
          onClick={() => router.push('/apartments/new')}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
        >
          <PlusIcon className="h-5 w-5" />
          Nuevo Apartamento
        </button>
      </div>

      {/* Statistics Cards */}
      {stats && !statsLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-card border rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Apartamentos</p>
                <p className="text-2xl font-bold mt-1">{stats.total_apartments}</p>
              </div>
              <BuildingOfficeIcon className="h-8 w-8 text-blue-500" />
            </div>
          </div>

          <div className="bg-card border rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Capacidad Total</p>
                <p className="text-2xl font-bold mt-1">{stats.total_capacity}</p>
              </div>
              <UserGroupIcon className="h-8 w-8 text-green-500" />
            </div>
          </div>

          <div className="bg-card border rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Ocupación</p>
                <p className="text-2xl font-bold mt-1">{stats.occupancy_percentage.toFixed(1)}%</p>
              </div>
              <ChartBarIcon className="h-8 w-8 text-yellow-500" />
            </div>
          </div>

          <div className="bg-card border rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Renta Promedio</p>
                <p className="text-2xl font-bold mt-1">¥{stats.average_rent.toLocaleString()}</p>
              </div>
              <CurrencyYenIcon className="h-8 w-8 text-purple-500" />
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-card border rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <FunnelIcon className="h-5 w-5" />
            <h2 className="font-semibold">Filtros</h2>
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="text-sm text-primary hover:underline"
          >
            {showFilters ? 'Ocultar' : 'Mostrar'} filtros
          </button>
        </div>

        {/* Search bar always visible */}
        <div className="relative mb-4">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Buscar por código o dirección..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        {/* Advanced filters */}
        {showFilters && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  <input
                    type="checkbox"
                    checked={availableOnly}
                    onChange={(e) => setAvailableOnly(e.target.checked)}
                    className="mr-2"
                  />
                  Solo disponibles
                </label>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Capacidad Mínima</label>
                <input
                  type="number"
                  placeholder="Ej: 2"
                  value={minCapacity}
                  onChange={(e) => setMinCapacity(e.target.value ? Number(e.target.value) : '')}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Renta Máxima (¥)</label>
                <input
                  type="number"
                  placeholder="Ej: 50000"
                  value={maxRent}
                  onChange={(e) => setMaxRent(e.target.value ? Number(e.target.value) : '')}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>

            <button
              onClick={clearFilters}
              className="flex items-center gap-2 px-3 py-1.5 text-sm border rounded-lg hover:bg-accent transition-colors"
            >
              <XMarkIcon className="h-4 w-4" />
              Limpiar filtros
            </button>
          </div>
        )}
      </div>

      {/* Apartments Grid */}
      <div className="bg-card border rounded-lg">
        <div className="p-4 border-b">
          <h2 className="font-semibold">
            Apartamentos ({apartments.length})
          </h2>
        </div>

        {apartmentsLoading && (
          <div className="p-8 text-center text-muted-foreground">
            Cargando apartamentos...
          </div>
        )}

        {apartmentsError && (
          <div className="p-8 text-center text-red-500">
            Error al cargar apartamentos. Por favor, intenta de nuevo.
          </div>
        )}

        {!apartmentsLoading && !apartmentsError && apartments.length === 0 && (
          <div className="p-8 text-center text-muted-foreground">
            No se encontraron apartamentos.
          </div>
        )}

        {!apartmentsLoading && !apartmentsError && apartments.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
            {apartments.map((apartment) => (
              <div
                key={apartment.id}
                className="border rounded-lg p-4 hover:shadow-lg transition-shadow cursor-pointer"
                onClick={() => router.push(`/apartments/${apartment.id}`)}
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-semibold text-lg">{apartment.apartment_code}</h3>
                    <p className="text-sm text-muted-foreground">{apartment.address}</p>
                  </div>
                  <StatusBadge status={apartment.status} />
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-2 mb-3 text-sm">
                  <div>
                    <span className="text-muted-foreground">Ocupación:</span>
                    <p className="font-medium">
                      {apartment.employees_count}/{apartment.capacity} ({apartment.occupancy_rate.toFixed(0)}%)
                    </p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Renta:</span>
                    <p className="font-medium">¥{apartment.monthly_rent.toLocaleString()}</p>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="mb-3">
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

                {/* Actions */}
                <div className="flex items-center gap-2 pt-3 border-t">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      router.push(`/apartments/${apartment.id}`);
                    }}
                    className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 text-sm border rounded hover:bg-accent transition-colors"
                  >
                    <EyeIcon className="h-4 w-4" />
                    Ver
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      router.push(`/apartments/${apartment.id}/edit`);
                    }}
                    className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 text-sm border rounded hover:bg-accent transition-colors"
                  >
                    <PencilIcon className="h-4 w-4" />
                    Editar
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
