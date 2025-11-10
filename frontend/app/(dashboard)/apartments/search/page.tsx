'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  XMarkIcon,
  MapPinIcon,
  CurrencyYenIcon,
  UserGroupIcon,
  EyeIcon,
  PencilIcon,
} from '@heroicons/react/24/outline';

interface SearchFilters {
  search: string;
  available_only: boolean;
  min_capacity: number | '';
  max_capacity: number | '';
  min_rent: number | '';
  max_rent: number | '';
  status: string;
  sort_by: string;
  sort_order: 'asc' | 'desc';
}

export default function SearchApartmentsPage() {
  const router = useRouter();
  const [filters, setFilters] = useState<SearchFilters>({
    search: '',
    available_only: false,
    min_capacity: '',
    max_capacity: '',
    min_rent: '',
    max_rent: '',
    status: '',
    sort_by: 'apartment_code',
    sort_order: 'asc',
  });
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Fetch apartments with filters
  const { data: apartments = [], isLoading, error } = useQuery({
    queryKey: ['apartments-search', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.search) params.append('search', filters.search);
      if (filters.available_only) params.append('available_only', 'true');
      if (filters.min_capacity) params.append('min_capacity', String(filters.min_capacity));
      if (filters.max_capacity) params.append('max_capacity', String(filters.max_capacity));
      if (filters.min_rent) params.append('min_rent', String(filters.min_rent));
      if (filters.max_rent) params.append('max_rent', String(filters.max_rent));
      if (filters.status) params.append('status', filters.status);
      params.append('sort_by', filters.sort_by);
      params.append('sort_order', filters.sort_order);

      const response = await api.get(`/apartments/?${params.toString()}`);
      return response.data;
    },
  });

  const handleFilterChange = (field: keyof SearchFilters, value: any) => {
    setFilters(prev => ({ ...prev, [field]: value }));
  };

  const clearFilters = () => {
    setFilters({
      search: '',
      available_only: false,
      min_capacity: '',
      max_capacity: '',
      min_rent: '',
      max_rent: '',
      status: '',
      sort_by: 'apartment_code',
      sort_order: 'asc',
    });
  };

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

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Búsqueda Avanzada de Apartamentos</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Encuentra apartamentos usando múltiples filtros y criterios
          </p>
        </div>
        <button
          onClick={() => router.push('/apartments/create')}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
        >
          Nuevo Apartamento
        </button>
      </div>

      {/* Search Form */}
      <div className="bg-card border rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <MagnifyingGlassIcon className="h-5 w-5" />
            <h2 className="font-semibold">Criterios de Búsqueda</h2>
          </div>
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-sm text-primary hover:underline"
          >
            {showAdvanced ? 'Ocultar' : 'Mostrar'} filtros avanzados
          </button>
        </div>

        <div className="space-y-4">
          {/* Search bar */}
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Buscar por código o dirección..."
              value={filters.search}
              onChange={(e) => handleFilterChange('search', e.target.value)}
              className="w-full pl-10 pr-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {/* Basic filters */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                <input
                  type="checkbox"
                  checked={filters.available_only}
                  onChange={(e) => handleFilterChange('available_only', e.target.checked)}
                  className="mr-2"
                />
                Solo disponibles
              </label>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Estado</label>
              <select
                value={filters.status}
                onChange={(e) => handleFilterChange('status', e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">Todos los estados</option>
                <option value="disponible">Disponible</option>
                <option value="parcial">Parcial</option>
                <option value="lleno">Lleno</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Ordenar por</label>
              <div className="flex gap-2">
                <select
                  value={filters.sort_by}
                  onChange={(e) => handleFilterChange('sort_by', e.target.value)}
                  className="flex-1 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="apartment_code">Código</option>
                  <option value="address">Dirección</option>
                  <option value="monthly_rent">Renta</option>
                  <option value="capacity">Capacidad</option>
                  <option value="occupancy_rate">Ocupación</option>
                </select>
                <select
                  value={filters.sort_order}
                  onChange={(e) => handleFilterChange('sort_order', e.target.value)}
                  className="px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="asc">↑</option>
                  <option value="desc">↓</option>
                </select>
              </div>
            </div>
          </div>

          {/* Advanced filters */}
          {showAdvanced && (
            <div className="pt-4 border-t space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">
                    <UserGroupIcon className="inline h-4 w-4 mr-1" />
                    Capacidad Mínima
                  </label>
                  <input
                    type="number"
                    value={filters.min_capacity}
                    onChange={(e) => handleFilterChange('min_capacity', e.target.value ? Number(e.target.value) : '')}
                    placeholder="Ej: 2"
                    min="0"
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Capacidad Máxima</label>
                  <input
                    type="number"
                    value={filters.max_capacity}
                    onChange={(e) => handleFilterChange('max_capacity', e.target.value ? Number(e.target.value) : '')}
                    placeholder="Ej: 8"
                    min="0"
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    <CurrencyYenIcon className="inline h-4 w-4 mr-1" />
                    Renta Mínima (¥)
                  </label>
                  <input
                    type="number"
                    value={filters.min_rent}
                    onChange={(e) => handleFilterChange('min_rent', e.target.value ? Number(e.target.value) : '')}
                    placeholder="Ej: 30000"
                    min="0"
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Renta Máxima (¥)</label>
                  <input
                    type="number"
                    value={filters.max_rent}
                    onChange={(e) => handleFilterChange('max_rent', e.target.value ? Number(e.target.value) : '')}
                    placeholder="Ej: 100000"
                    min="0"
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-3 pt-4 border-t">
            <button
              onClick={clearFilters}
              className="flex items-center gap-2 px-4 py-2 border rounded-lg hover:bg-accent transition-colors"
            >
              <XMarkIcon className="h-4 w-4" />
              Limpiar filtros
            </button>
            <div className="text-sm text-muted-foreground">
              {isLoading ? 'Buscando...' : `${apartments.length} resultados encontrados`}
            </div>
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="bg-card border rounded-lg">
        <div className="p-4 border-b">
          <h2 className="font-semibold">Resultados de Búsqueda</h2>
        </div>

        {isLoading && (
          <div className="p-8 text-center text-muted-foreground">
            Buscando apartamentos...
          </div>
        )}

        {error && (
          <div className="p-8 text-center text-red-500">
            Error al buscar apartamentos. Por favor, intenta de nuevo.
          </div>
        )}

        {!isLoading && !error && apartments.length === 0 && (
          <div className="p-8 text-center text-muted-foreground">
            No se encontraron apartamentos con los criterios especificados.
          </div>
        )}

        {!isLoading && !error && apartments.length > 0 && (
          <div className="divide-y">
            {apartments.map((apartment: any) => (
              <div
                key={apartment.id}
                className="p-4 hover:bg-accent transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-semibold text-lg">{apartment.apartment_code}</h3>
                      <StatusBadge status={apartment.status} />
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <MapPinIcon className="h-4 w-4" />
                        {apartment.address}
                      </div>
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <CurrencyYenIcon className="h-4 w-4" />
                        ¥{apartment.monthly_rent.toLocaleString()}/mes
                      </div>
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <UserGroupIcon className="h-4 w-4" />
                        {apartment.employees_count}/{apartment.capacity} personas ({apartment.occupancy_rate.toFixed(0)}%)
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 ml-4">
                    <button
                      onClick={() => router.push(`/apartments/${apartment.id}`)}
                      className="flex items-center gap-2 px-3 py-1.5 text-sm border rounded hover:bg-accent transition-colors"
                    >
                      <EyeIcon className="h-4 w-4" />
                      Ver
                    </button>
                    <button
                      onClick={() => router.push(`/apartments/${apartment.id}/edit`)}
                      className="flex items-center gap-2 px-3 py-1.5 text-sm border rounded hover:bg-accent transition-colors"
                    >
                      <PencilIcon className="h-4 w-4" />
                      Editar
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
