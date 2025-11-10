'use client';

import React, { useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import {
  ArrowLeftIcon,
  ExclamationTriangleIcon,
  CalendarIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';

interface EndAssignmentForm {
  end_date: string;
  end_reason: string;
  notes: string;
}

export default function EndAssignmentPage() {
  const router = useRouter();
  const params = useParams();
  const queryClient = useQueryClient();
  const assignmentId = params.id as string;
  const [form, setForm] = useState<EndAssignmentForm>({
    end_date: new Date().toISOString().split('T')[0],
    end_reason: '',
    notes: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Fetch assignment details
  const { data: assignment, isLoading } = useQuery({
    queryKey: ['apartment-assignment', assignmentId],
    queryFn: async () => {
      const response = await api.get(`/apartment-assignments/${assignmentId}`);
      return response.data;
    },
  });

  // End assignment mutation
  const endMutation = useMutation({
    mutationFn: async (data: EndAssignmentForm) => {
      const response = await api.post(`/apartment-assignments/${assignmentId}/end`, {
        end_date: data.end_date,
        end_reason: data.end_reason,
        notes: data.notes || null,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apartment-assignment', assignmentId] });
      queryClient.invalidateQueries({ queryKey: ['apartment-assignments'] });
      queryClient.invalidateQueries({ queryKey: ['apartment-assignments-stats'] });
      router.push(`/apartment-assignments/${assignmentId}`);
    },
    onError: (error: any) => {
      if (error.response?.data?.detail) {
        setErrors({ general: error.response.data.detail });
      }
    },
  });

  const handleChange = (field: keyof EndAssignmentForm, value: string) => {
    setForm(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});

    const newErrors: Record<string, string> = {};
    if (!form.end_date) newErrors.end_date = 'La fecha es requerida';
    if (!form.end_reason.trim()) newErrors.end_reason = 'El motivo es requerido';

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    endMutation.mutate(form);
  };

  if (isLoading || !assignment) {
    return (
      <div className="p-6">
        <div className="text-center py-12">Cargando...</div>
      </div>
    );
  }

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
          <h1 className="text-3xl font-bold">Finalizar Asignación</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Dar por terminada la asignación de {assignment.employee.full_name_kanji} a {assignment.apartment.apartment_code}
          </p>
        </div>
      </div>

      {/* Warning */}
      <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <div className="flex items-start gap-3">
          <ExclamationTriangleIcon className="h-6 w-6 text-yellow-600 mt-0.5" />
          <div>
            <h3 className="font-semibold text-yellow-800">Esta acción no se puede deshacer</h3>
            <p className="text-sm text-yellow-700 mt-1">
              Una vez finalizada la asignación, el empleado será desasignado del apartamento
              y la asignación pasará al estado "Finalizada".
            </p>
          </div>
        </div>
      </div>

      {/* Current Assignment Info */}
      <div className="bg-card border rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Asignación Actual</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <p className="text-sm text-muted-foreground">Empleado</p>
            <p className="font-medium">{assignment.employee.full_name_kanji}</p>
            <p className="text-sm text-muted-foreground">ID: {assignment.employee.hakenmoto_id}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Apartamento</p>
            <p className="font-medium">{assignment.apartment.apartment_code}</p>
            <p className="text-sm text-muted-foreground">{assignment.apartment.address}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Fecha de Inicio</p>
            <p className="font-medium">
              {new Date(assignment.assignment_date).toLocaleDateString('es-ES', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Fecha Estimada de Fin</p>
            <p className="font-medium">
              {new Date(form.end_date).toLocaleDateString('es-ES', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </p>
          </div>
        </div>
      </div>

      {/* Form */}
      <div className="bg-card border rounded-lg p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          {errors.general && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
              {errors.general}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* End Date */}
            <div>
              <label className="block text-sm font-medium mb-2">
                <CalendarIcon className="inline h-4 w-4 mr-1" />
                Fecha de Finalización *
              </label>
              <input
                type="date"
                value={form.end_date}
                onChange={(e) => handleChange('end_date', e.target.value)}
                max={new Date().toISOString().split('T')[0]}
                className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary ${
                  errors.end_date ? 'border-red-500' : ''
                }`}
              />
              {errors.end_date && (
                <p className="text-sm text-red-500 mt-1">{errors.end_date}</p>
              )}
            </div>

            {/* End Reason */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Motivo de Finalización *
              </label>
              <select
                value={form.end_reason}
                onChange={(e) => handleChange('end_reason', e.target.value)}
                className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary ${
                  errors.end_reason ? 'border-red-500' : ''
                }`}
              >
                <option value="">Seleccionar motivo</option>
                <option value="contract_ended">Fin de contrato</option>
                <option value="relocation">Reubicación</option>
                <option value="employee_request">Solicitud del empleado</option>
                <option value="disciplinary">Motivos disciplinarios</option>
                <option value="company_decision">Decisión de la empresa</option>
                <option value="other">Otro</option>
              </select>
              {errors.end_reason && (
                <p className="text-sm text-red-500 mt-1">{errors.end_reason}</p>
              )}
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium mb-2">
              <DocumentTextIcon className="inline h-4 w-4 mr-1" />
              Notas Adicionales
            </label>
            <textarea
              value={form.notes}
              onChange={(e) => handleChange('notes', e.target.value)}
              placeholder="Información adicional sobre la finalización"
              rows={4}
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3 pt-4 border-t">
            <button
              type="submit"
              disabled={endMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
            >
              {endMutation.isPending ? 'Finalizando...' : 'Finalizar Asignación'}
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
