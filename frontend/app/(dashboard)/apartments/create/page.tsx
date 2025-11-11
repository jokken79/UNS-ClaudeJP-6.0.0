'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { apartmentsV2Service } from '@/lib/api';
import type { ApartmentCreate } from '@/types/apartments-v2';
import { RoomType } from '@/types/apartments-v2';

export default function CreateApartmentPage() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Form state with only existing backend fields
  const [formData, setFormData] = useState<Partial<ApartmentCreate>>({
    name: '',
    building_name: '',
    room_number: '',
    floor_number: undefined,
    postal_code: '',
    prefecture: '',
    city: '',
    address_line1: '',
    address_line2: '',
    room_type: RoomType.R,
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
    status: 'active',
  });

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
    setSuccess(false);

    // Validation
    if (!formData.name?.trim()) {
      setError('El nombre del apartamento es requerido');
      return;
    }

    if (!formData.base_rent || formData.base_rent <= 0) {
      setError('La renta base debe ser mayor a 0');
      return;
    }

    setIsSubmitting(true);

    try {
      const apartmentData: ApartmentCreate = {
        name: formData.name!,
        building_name: formData.building_name,
        room_number: formData.room_number,
        floor_number: formData.floor_number,
        postal_code: formData.postal_code,
        prefecture: formData.prefecture,
        city: formData.city,
        address_line1: formData.address_line1,
        address_line2: formData.address_line2,
        room_type: formData.room_type,
        size_sqm: formData.size_sqm,
        base_rent: formData.base_rent!,
        management_fee: formData.management_fee || 0,
        deposit: formData.deposit || 0,
        key_money: formData.key_money || 0,
        default_cleaning_fee: formData.default_cleaning_fee || 20000,
        contract_start_date: formData.contract_start_date,
        contract_end_date: formData.contract_end_date,
        landlord_name: formData.landlord_name,
        landlord_contact: formData.landlord_contact,
        real_estate_agency: formData.real_estate_agency,
        emergency_contact: formData.emergency_contact,
        notes: formData.notes,
        status: formData.status || 'active',
      };

      const newApartment = await apartmentsV2Service.createApartment(apartmentData);

      setSuccess(true);

      // Redirect to detail page after 1 second
      setTimeout(() => {
        router.push(`/apartments/${newApartment.id}`);
      }, 1000);

    } catch (err: any) {
      console.error('Error creating apartment:', err);
      setError(err.response?.data?.detail || 'Error al crear el apartamento');
    } finally {
      setIsSubmitting(false);
    }
  };

  const totalCost = (formData.base_rent || 0) + (formData.management_fee || 0);

  return (
    <div className="container mx-auto py-6 px-4 max-w-5xl">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-4"
        >
          ← Volver
        </button>
        <h1 className="text-3xl font-bold">Crear Nuevo Apartamento</h1>
        <p className="text-muted-foreground mt-2">
          Complete la información del apartamento. Los campos marcados con * son obligatorios.
        </p>
      </div>

      {/* Success Message */}
      {success && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4 mb-6">
          <p className="font-medium text-green-800 dark:text-green-400">
            ¡Apartamento creado exitosamente!
          </p>
          <p className="text-sm text-green-700 dark:text-green-500 mt-1">
            Redirigiendo a la página de detalles...
          </p>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
          <p className="font-medium text-red-800 dark:text-red-400">Error</p>
          <p className="text-sm text-red-700 dark:text-red-500 mt-1">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Información Básica */}
        <div className="bg-card border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Información Básica</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-2">
                Nombre del Apartamento <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="name"
                value={formData.name || ''}
                onChange={handleInputChange}
                placeholder="ej. マンション太陽 201"
                required
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Nombre del Edificio</label>
              <input
                type="text"
                name="building_name"
                value={formData.building_name || ''}
                onChange={handleInputChange}
                placeholder="ej. 太陽ビル"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Número de Habitación</label>
              <input
                type="text"
                name="room_number"
                value={formData.room_number || ''}
                onChange={handleInputChange}
                placeholder="ej. 201"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Número de Piso</label>
              <input
                type="number"
                name="floor_number"
                value={formData.floor_number || ''}
                onChange={handleInputChange}
                min="0"
                placeholder="ej. 2"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Estado</label>
              <select
                name="status"
                value={formData.status || 'active'}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              >
                <option value="active">Activo</option>
                <option value="maintenance">En Mantenimiento</option>
                <option value="inactive">Inactivo</option>
              </select>
            </div>
          </div>
        </div>

        {/* Ubicación */}
        <div className="bg-card border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Ubicación</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Prefectura</label>
              <input
                type="text"
                name="prefecture"
                value={formData.prefecture || ''}
                onChange={handleInputChange}
                placeholder="ej. 東京都"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Ciudad</label>
              <input
                type="text"
                name="city"
                value={formData.city || ''}
                onChange={handleInputChange}
                placeholder="ej. 新宿区"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Código Postal</label>
              <input
                type="text"
                name="postal_code"
                value={formData.postal_code || ''}
                onChange={handleInputChange}
                placeholder="ej. 160-0022"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-2">Dirección Línea 1</label>
              <input
                type="text"
                name="address_line1"
                value={formData.address_line1 || ''}
                onChange={handleInputChange}
                placeholder="ej. 新宿1-2-3"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-2">Dirección Línea 2</label>
              <input
                type="text"
                name="address_line2"
                value={formData.address_line2 || ''}
                onChange={handleInputChange}
                placeholder="ej. Apartamento 5B"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>
          </div>
        </div>

        {/* Características */}
        <div className="bg-card border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Características</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Tipo de Habitación</label>
              <select
                name="room_type"
                value={formData.room_type || RoomType.R}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              >
                <option value={RoomType.R}>R (Habitación)</option>
                <option value={RoomType.K}>K (Cocina)</option>
                <option value={RoomType.DK}>DK (Comedor-Cocina)</option>
                <option value={RoomType.LDK}>LDK (Sala-Comedor-Cocina)</option>
                <option value={RoomType.S}>S (Studio)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Área (m²)</label>
              <input
                type="number"
                name="size_sqm"
                value={formData.size_sqm || ''}
                onChange={handleInputChange}
                min="0"
                step="0.1"
                placeholder="ej. 25.5"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>
          </div>
        </div>

        {/* Costos */}
        <div className="bg-card border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Costos</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                Renta Base <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                name="base_rent"
                value={formData.base_rent || ''}
                onChange={handleInputChange}
                min="0"
                required
                placeholder="ej. 50000"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Cuota de Administración</label>
              <input
                type="number"
                name="management_fee"
                value={formData.management_fee || ''}
                onChange={handleInputChange}
                min="0"
                placeholder="ej. 3000"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Depósito (敷金)</label>
              <input
                type="number"
                name="deposit"
                value={formData.deposit || ''}
                onChange={handleInputChange}
                min="0"
                placeholder="ej. 50000"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Key Money (礼金)</label>
              <input
                type="number"
                name="key_money"
                value={formData.key_money || ''}
                onChange={handleInputChange}
                min="0"
                placeholder="ej. 50000"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Cargo de Limpieza al Salir</label>
              <input
                type="number"
                name="default_cleaning_fee"
                value={formData.default_cleaning_fee || ''}
                onChange={handleInputChange}
                min="0"
                placeholder="ej. 20000"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>

            <div className="md:col-span-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mt-4">
              <p className="text-sm font-medium text-blue-800 dark:text-blue-400">
                Costo Total Mensual (Renta + Administración)
              </p>
              <p className="text-2xl font-bold text-blue-800 dark:text-blue-400 mt-1">
                ¥{totalCost.toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        {/* Contrato */}
        <div className="bg-card border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Información del Contrato</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Fecha de Inicio</label>
              <input
                type="date"
                name="contract_start_date"
                value={formData.contract_start_date || ''}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Fecha de Fin</label>
              <input
                type="date"
                name="contract_end_date"
                value={formData.contract_end_date || ''}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Propietario</label>
              <input
                type="text"
                name="landlord_name"
                value={formData.landlord_name || ''}
                onChange={handleInputChange}
                placeholder="ej. 田中太郎"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Contacto del Propietario</label>
              <input
                type="text"
                name="landlord_contact"
                value={formData.landlord_contact || ''}
                onChange={handleInputChange}
                placeholder="ej. 03-1234-5678"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Inmobiliaria</label>
              <input
                type="text"
                name="real_estate_agency"
                value={formData.real_estate_agency || ''}
                onChange={handleInputChange}
                placeholder="ej. ABC不動産"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Contacto de Emergencia</label>
              <input
                type="text"
                name="emergency_contact"
                value={formData.emergency_contact || ''}
                onChange={handleInputChange}
                placeholder="ej. 090-1234-5678"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>
          </div>
        </div>

        {/* Notas */}
        <div className="bg-card border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Notas Adicionales</h2>
          <textarea
            name="notes"
            value={formData.notes || ''}
            onChange={handleInputChange}
            rows={4}
            placeholder="Cualquier información adicional sobre el apartamento..."
            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
          />
        </div>

        {/* Buttons */}
        <div className="flex gap-4 justify-end">
          <button
            type="button"
            onClick={() => router.back()}
            disabled={isSubmitting}
            className="px-6 py-2 border rounded-lg hover:bg-accent transition-colors disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={isSubmitting || success}
            className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {isSubmitting ? 'Creando...' : 'Crear Apartamento'}
          </button>
        </div>
      </form>
    </div>
  );
}
