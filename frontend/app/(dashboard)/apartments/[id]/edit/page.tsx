'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { apartmentsV2Service } from '@/lib/api';
import type { ApartmentUpdate, ApartmentWithStats, RoomType } from '@/types/apartments-v2';
import {
  ArrowLeftIcon,
  BuildingOfficeIcon,
  MapPinIcon,
  HomeIcon,
  BanknotesIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';

export default function EditApartmentPage() {
  const router = useRouter();
  const params = useParams();
  const apartmentId = Number(params.id);

  const [apartment, setApartment] = useState<ApartmentWithStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const [formData, setFormData] = useState<Partial<ApartmentUpdate>>({
    name: '',
    building_name: '',
    room_number: '',
    floor_number: undefined,
    status: 'active',

    postal_code: '',
    prefecture: '',
    city: '',
    address_line1: '',
    address_line2: '',

    room_type: 'R' as RoomType,
    size_sqm: undefined,

    base_rent: 0,
    management_fee: 0,
    deposit: 0,
    key_money: 0,
    default_cleaning_fee: 20000,

    contract_start_date: undefined,
    contract_end_date: undefined,
    landlord_name: '',
    landlord_contact: '',
    real_estate_agency: '',
    emergency_contact: '',

    notes: '',
  });

  // Load existing apartment data
  useEffect(() => {
    const loadApartment = async () => {
      try {
        setIsLoading(true);
        const data = await apartmentsV2Service.getApartment(apartmentId);
        setApartment(data);

        // Pre-populate form with existing data
        setFormData({
          name: data.name,
          building_name: data.building_name || '',
          room_number: data.room_number || '',
          floor_number: data.floor_number || undefined,
          status: data.status || 'active',

          postal_code: data.postal_code || '',
          prefecture: data.prefecture || '',
          city: data.city || '',
          address_line1: data.address_line1 || '',
          address_line2: data.address_line2 || '',

          room_type: data.room_type || ('R' as RoomType),
          size_sqm: data.size_sqm || undefined,

          base_rent: data.base_rent,
          management_fee: data.management_fee || 0,
          deposit: data.deposit || 0,
          key_money: data.key_money || 0,
          default_cleaning_fee: data.default_cleaning_fee || 20000,

          contract_start_date: data.contract_start_date || undefined,
          contract_end_date: data.contract_end_date || undefined,
          landlord_name: data.landlord_name || '',
          landlord_contact: data.landlord_contact || '',
          real_estate_agency: data.real_estate_agency || '',
          emergency_contact: data.emergency_contact || '',

          notes: data.notes || '',
        });
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Error al cargar el apartamento');
      } finally {
        setIsLoading(false);
      }
    };

    loadApartment();
  }, [apartmentId]);

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value, type } = e.target;

    if (type === 'number') {
      setFormData(prev => ({
        ...prev,
        [name]: value === '' ? undefined : Number(value)
      }));
    } else {
      setFormData(prev => ({ ...prev, [name]: value || undefined }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (!formData.name?.trim()) {
      setError('El nombre del apartamento es requerido');
      return;
    }

    if (formData.base_rent !== undefined && formData.base_rent <= 0) {
      setError('La renta base debe ser mayor a 0');
      return;
    }

    setIsSubmitting(true);

    try {
      const updateData: ApartmentUpdate = {
        name: formData.name,
        building_name: formData.building_name,
        room_number: formData.room_number,
        floor_number: formData.floor_number,
        status: formData.status,

        postal_code: formData.postal_code,
        prefecture: formData.prefecture,
        city: formData.city,
        address_line1: formData.address_line1,
        address_line2: formData.address_line2,

        room_type: formData.room_type,
        size_sqm: formData.size_sqm,

        base_rent: formData.base_rent,
        management_fee: formData.management_fee,
        deposit: formData.deposit,
        key_money: formData.key_money,
        default_cleaning_fee: formData.default_cleaning_fee,

        contract_start_date: formData.contract_start_date,
        contract_end_date: formData.contract_end_date,
        landlord_name: formData.landlord_name,
        landlord_contact: formData.landlord_contact,
        real_estate_agency: formData.real_estate_agency,
        emergency_contact: formData.emergency_contact,

        notes: formData.notes,
      };

      await apartmentsV2Service.updateApartment(apartmentId, updateData);
      setSuccess(true);

      setTimeout(() => {
        router.push(`/apartments/${apartmentId}`);
      }, 1000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al actualizar el apartamento');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Calculate total monthly cost
  const totalMonthlyCost = (formData.base_rent || 0) + (formData.management_fee || 0);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Cargando apartamento...</p>
        </div>
      </div>
    );
  }

  if (error && !apartment) {
    return (
      <div className="p-6">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-red-800 dark:text-red-400">{error}</p>
          <button
            onClick={() => router.push('/apartments')}
            className="mt-4 text-red-600 dark:text-red-400 hover:underline"
          >
            Volver a Apartamentos
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => router.push(`/apartments/${apartmentId}`)}
          className="flex items-center gap-2 text-muted-foreground hover:text-foreground mb-4"
        >
          <ArrowLeftIcon className="h-5 w-5" />
          Volver a Detalles
        </button>

        <div className="flex items-center gap-3">
          <div className="p-3 bg-primary/10 rounded-lg">
            <BuildingOfficeIcon className="h-8 w-8 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold">Editar Apartamento</h1>
            <p className="text-muted-foreground mt-1">
              {apartment?.name} - {apartment?.building_name}
            </p>
          </div>
        </div>
      </div>

      {/* Success Message */}
      {success && (
        <div className="mb-6 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
          <p className="text-green-800 dark:text-green-400 font-medium">
            ✓ Apartamento actualizado exitosamente. Redirigiendo...
          </p>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="mb-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-red-800 dark:text-red-400">{error}</p>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Información Básica */}
        <div className="bg-card border border-border rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <HomeIcon className="h-5 w-5 text-primary" />
            <h2 className="text-xl font-semibold">Información Básica</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">
                Nombre del Apartamento <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                required
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="マンション太陽 201"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Nombre del Edificio
              </label>
              <input
                type="text"
                name="building_name"
                value={formData.building_name}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="太陽ビル"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Número de Habitación
              </label>
              <input
                type="text"
                name="room_number"
                value={formData.room_number}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="201"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Piso
              </label>
              <input
                type="number"
                name="floor_number"
                value={formData.floor_number || ''}
                onChange={handleInputChange}
                min="0"
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="2"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Estado
              </label>
              <select
                name="status"
                value={formData.status}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="active">Activo</option>
                <option value="maintenance">Mantenimiento</option>
                <option value="inactive">Inactivo</option>
              </select>
            </div>
          </div>
        </div>

        {/* Ubicación */}
        <div className="bg-card border border-border rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <MapPinIcon className="h-5 w-5 text-primary" />
            <h2 className="text-xl font-semibold">Ubicación</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">
                Código Postal
              </label>
              <input
                type="text"
                name="postal_code"
                value={formData.postal_code}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="160-0023"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Prefectura
              </label>
              <input
                type="text"
                name="prefecture"
                value={formData.prefecture}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="東京都"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Ciudad
              </label>
              <input
                type="text"
                name="city"
                value={formData.city}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="新宿区"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Dirección Línea 1
              </label>
              <input
                type="text"
                name="address_line1"
                value={formData.address_line1}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="西新宿1-2-3"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1">
                Dirección Línea 2 (opcional)
              </label>
              <input
                type="text"
                name="address_line2"
                value={formData.address_line2}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="Información adicional de dirección"
              />
            </div>
          </div>
        </div>

        {/* Características */}
        <div className="bg-card border border-border rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <BuildingOfficeIcon className="h-5 w-5 text-primary" />
            <h2 className="text-xl font-semibold">Características</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">
                Tipo de Habitación
              </label>
              <select
                name="room_type"
                value={formData.room_type}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="R">R (Individual)</option>
                <option value="1K">1K (1 habitación + cocina)</option>
                <option value="1DK">1DK (1 habitación + comedor-cocina)</option>
                <option value="1LDK">1LDK (1 habitación + sala-comedor-cocina)</option>
                <option value="2K">2K (2 habitaciones + cocina)</option>
                <option value="2DK">2DK (2 habitaciones + comedor-cocina)</option>
                <option value="2LDK">2LDK (2 habitaciones + sala-comedor-cocina)</option>
                <option value="3K">3K (3 habitaciones + cocina)</option>
                <option value="3DK">3DK (3 habitaciones + comedor-cocina)</option>
                <option value="3LDK">3LDK (3 habitaciones + sala-comedor-cocina)</option>
                <option value="4K">4K (4 habitaciones + cocina)</option>
                <option value="4DK">4DK (4 habitaciones + comedor-cocina)</option>
                <option value="4LDK">4LDK (4 habitaciones + sala-comedor-cocina)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Tamaño (m²)
              </label>
              <input
                type="number"
                name="size_sqm"
                value={formData.size_sqm || ''}
                onChange={handleInputChange}
                min="0"
                step="0.01"
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="25.5"
              />
            </div>
          </div>
        </div>

        {/* Costos */}
        <div className="bg-card border border-border rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <BanknotesIcon className="h-5 w-5 text-primary" />
            <h2 className="text-xl font-semibold">Costos</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">
                Renta Base (¥) <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                name="base_rent"
                value={formData.base_rent}
                onChange={handleInputChange}
                required
                min="0"
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="50000"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Cuota de Administración (¥)
              </label>
              <input
                type="number"
                name="management_fee"
                value={formData.management_fee}
                onChange={handleInputChange}
                min="0"
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="5000"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Depósito / 敷金 (¥)
              </label>
              <input
                type="number"
                name="deposit"
                value={formData.deposit}
                onChange={handleInputChange}
                min="0"
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="100000"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Key Money / 礼金 (¥)
              </label>
              <input
                type="number"
                name="key_money"
                value={formData.key_money}
                onChange={handleInputChange}
                min="0"
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="100000"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Cargo de Limpieza al Salir (¥)
              </label>
              <input
                type="number"
                name="default_cleaning_fee"
                value={formData.default_cleaning_fee}
                onChange={handleInputChange}
                min="0"
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="20000"
              />
            </div>

            {/* Total Monthly Cost Display */}
            <div className="md:col-span-2 bg-primary/5 border border-primary/20 rounded-lg p-4">
              <div className="flex justify-between items-center">
                <span className="font-medium text-lg">Costo Mensual Total:</span>
                <span className="text-2xl font-bold text-primary">
                  ¥{totalMonthlyCost.toLocaleString()}
                </span>
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                Renta Base (¥{(formData.base_rent || 0).toLocaleString()}) + Administración (¥{(formData.management_fee || 0).toLocaleString()})
              </p>
            </div>
          </div>
        </div>

        {/* Contrato */}
        <div className="bg-card border border-border rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <DocumentTextIcon className="h-5 w-5 text-primary" />
            <h2 className="text-xl font-semibold">Información del Contrato</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">
                Fecha de Inicio del Contrato
              </label>
              <input
                type="date"
                name="contract_start_date"
                value={formData.contract_start_date || ''}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Fecha de Fin del Contrato
              </label>
              <input
                type="date"
                name="contract_end_date"
                value={formData.contract_end_date || ''}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Nombre del Propietario
              </label>
              <input
                type="text"
                name="landlord_name"
                value={formData.landlord_name}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="田中太郎"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Contacto del Propietario
              </label>
              <input
                type="text"
                name="landlord_contact"
                value={formData.landlord_contact}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="03-1234-5678"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Agencia Inmobiliaria
              </label>
              <input
                type="text"
                name="real_estate_agency"
                value={formData.real_estate_agency}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="不動産エージェント株式会社"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Contacto de Emergencia
              </label>
              <input
                type="text"
                name="emergency_contact"
                value={formData.emergency_contact}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="090-1234-5678"
              />
            </div>
          </div>
        </div>

        {/* Notas */}
        <div className="bg-card border border-border rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <DocumentTextIcon className="h-5 w-5 text-primary" />
            <h2 className="text-xl font-semibold">Notas Adicionales</h2>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Notas
            </label>
            <textarea
              name="notes"
              value={formData.notes}
              onChange={handleInputChange}
              rows={4}
              className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="Información adicional sobre el apartamento..."
            />
          </div>
        </div>

        {/* Submit Buttons */}
        <div className="flex justify-end gap-4">
          <button
            type="button"
            onClick={() => router.push(`/apartments/${apartmentId}`)}
            className="px-6 py-2 border border-border rounded-md hover:bg-accent transition-colors"
            disabled={isSubmitting}
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-6 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isSubmitting ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-foreground"></div>
                Guardando...
              </>
            ) : (
              'Guardar Cambios'
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
