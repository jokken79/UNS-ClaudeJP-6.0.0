'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import {
  ArrowLeftIcon,
  BuildingOfficeIcon,
  MapPinIcon,
  CurrencyYenIcon,
  UserGroupIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';

interface CreateApartmentForm {
  apartment_code: string;
  address: string;
  monthly_rent: number | '';
  capacity: number | '';
  notes: string;
}

export default function CreateApartmentPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<CreateApartmentForm>({
    apartment_code: '',
    address: '',
    monthly_rent: '',
    capacity: '',
    notes: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Create apartment mutation
  const createMutation = useMutation({
    mutationFn: async (data: CreateApartmentForm) => {
      const response = await api.post('/apartments/', {
        apartment_code: data.apartment_code,
        address: data.address,
        monthly_rent: Number(data.monthly_rent),
        capacity: Number(data.capacity),
        notes: data.notes || null,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apartments'] });
      queryClient.invalidateQueries({ queryKey: ['apartments-stats'] });
      router.push('/apartments');
    },
    onError: (error: any) => {
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        if (Array.isArray(detail)) {
          const newErrors: Record<string, string> = {};
          detail.forEach((err: any) => {
            if (err.loc) {
              newErrors[err.loc.join('.')] = err.msg;
            }
          });
          setErrors(newErrors);
        }
      }
    },
  });

  const handleChange = (field: keyof CreateApartmentForm, value: string | number) => {
    setForm(prev => ({ ...prev, [field]: value }));
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});

    // Basic validation
    const newErrors: Record<string, string> = {};
    if (!form.apartment_code.trim()) newErrors.apartment_code = 'El código es requerido';
    if (!form.address.trim()) newErrors.address = 'La dirección es requerida';
    if (!form.monthly_rent || Number(form.monthly_rent) <= 0) newErrors.monthly_rent = 'La renta debe ser mayor a 0';
    if (!form.capacity || Number(form.capacity) <= 0) newErrors.capacity = 'La capacidad debe ser mayor a 0';

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    createMutation.mutate(form);
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => router.back()}
          className="p-2 hover:bg-accent rounded-lg transition-colors"
        >
          <ArrowLeftIcon className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-3xl font-bold">Crear Nuevo Apartamento</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Registra un nuevo apartamento en el sistema
          </p>
        </div>
      </div>

      {/* Form */}
      <div className="bg-card border rounded-lg p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Apartment Code */}
            <div>
              <label className="block text-sm font-medium mb-2">
                <BuildingOfficeIcon className="inline h-4 w-4 mr-1" />
                Código del Apartamento *
              </label>
              <input
                type="text"
                value={form.apartment_code}
                onChange={(e) => handleChange('apartment_code', e.target.value)}
                placeholder="Ej: APT-001"
                className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary ${
                  errors.apartment_code ? 'border-red-500' : ''
                }`}
              />
              {errors.apartment_code && (
                <p className="text-sm text-red-500 mt-1">{errors.apartment_code}</p>
              )}
            </div>

            {/* Address */}
            <div>
              <label className="block text-sm font-medium mb-2">
                <MapPinIcon className="inline h-4 w-4 mr-1" />
                Dirección *
              </label>
              <input
                type="text"
                value={form.address}
                onChange={(e) => handleChange('address', e.target.value)}
                placeholder="Dirección completa"
                className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary ${
                  errors.address ? 'border-red-500' : ''
                }`}
              />
              {errors.address && (
                <p className="text-sm text-red-500 mt-1">{errors.address}</p>
              )}
            </div>

            {/* Monthly Rent */}
            <div>
              <label className="block text-sm font-medium mb-2">
                <CurrencyYenIcon className="inline h-4 w-4 mr-1" />
                Renta Mensual (¥) *
              </label>
              <input
                type="number"
                value={form.monthly_rent}
                onChange={(e) => handleChange('monthly_rent', e.target.value ? Number(e.target.value) : '')}
                placeholder="Ej: 50000"
                min="0"
                className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary ${
                  errors.monthly_rent ? 'border-red-500' : ''
                }`}
              />
              {errors.monthly_rent && (
                <p className="text-sm text-red-500 mt-1">{errors.monthly_rent}</p>
              )}
            </div>

            {/* Capacity */}
            <div>
              <label className="block text-sm font-medium mb-2">
                <UserGroupIcon className="inline h-4 w-4 mr-1" />
                Capacidad (personas) *
              </label>
              <input
                type="number"
                value={form.capacity}
                onChange={(e) => handleChange('capacity', e.target.value ? Number(e.target.value) : '')}
                placeholder="Ej: 4"
                min="1"
                className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary ${
                  errors.capacity ? 'border-red-500' : ''
                }`}
              />
              {errors.capacity && (
                <p className="text-sm text-red-500 mt-1">{errors.capacity}</p>
              )}
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium mb-2">
              <DocumentTextIcon className="inline h-4 w-4 mr-1" />
              Notas
            </label>
            <textarea
              value={form.notes}
              onChange={(e) => handleChange('notes', e.target.value)}
              placeholder="Información adicional sobre el apartamento"
              rows={4}
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3 pt-4 border-t">
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {createMutation.isPending ? 'Creando...' : 'Crear Apartamento'}
            </button>
            <button
              type="button"
              onClick={() => router.back()}
              className="flex items-center gap-2 px-4 py-2 border rounded-lg hover:bg-accent transition-colors"
            >
              Cancelar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
