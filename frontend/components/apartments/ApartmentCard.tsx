'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import {
  BuildingOfficeIcon,
  MapPinIcon,
  CurrencyYenIcon,
  UserGroupIcon,
  EyeIcon,
  PencilIcon,
} from '@heroicons/react/24/outline';

interface ApartmentCardProps {
  apartment: {
    id: number;
    apartment_code: string;
    address: string;
    monthly_rent: number;
    capacity: number;
    employees_count: number;
    occupancy_rate: number;
    status: 'disponible' | 'parcial' | 'lleno';
  };
  onView?: (id: number) => void;
  onEdit?: (id: number) => void;
}

export function ApartmentCard({ apartment, onView, onEdit }: ApartmentCardProps) {
  const router = useRouter();

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

  const handleView = () => {
    if (onView) {
      onView(apartment.id);
    } else {
      router.push(`/apartments/${apartment.id}`);
    }
  };

  const handleEdit = () => {
    if (onEdit) {
      onEdit(apartment.id);
    } else {
      router.push(`/apartments/${apartment.id}/edit`);
    }
  };

  return (
    <div
      className="border rounded-lg p-4 hover:shadow-lg transition-shadow cursor-pointer"
      onClick={handleView}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-lg">{apartment.apartment_code}</h3>
          <p className="text-sm text-muted-foreground flex items-center gap-1">
            <MapPinIcon className="h-4 w-4" />
            {apartment.address}
          </p>
        </div>
        <StatusBadge status={apartment.status} />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-2 mb-3 text-sm">
        <div>
          <span className="text-muted-foreground">Ocupación:</span>
          <p className="font-medium flex items-center gap-1">
            <UserGroupIcon className="h-4 w-4" />
            {apartment.employees_count}/{apartment.capacity} ({apartment.occupancy_rate.toFixed(0)}%)
          </p>
        </div>
        <div>
          <span className="text-muted-foreground">Renta:</span>
          <p className="font-medium flex items-center gap-1">
            <CurrencyYenIcon className="h-4 w-4" />
            ¥{apartment.monthly_rent.toLocaleString()}
          </p>
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
            handleView();
          }}
          className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 text-sm border rounded hover:bg-accent transition-colors"
        >
          <EyeIcon className="h-4 w-4" />
          Ver
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleEdit();
          }}
          className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 text-sm border rounded hover:bg-accent transition-colors"
        >
          <PencilIcon className="h-4 w-4" />
          Editar
        </button>
      </div>
    </div>
  );
}
