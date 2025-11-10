'use client';

/**
 * Payroll Dashboard - Página principal
 * Dashboard principal del sistema de payroll
 */
import { useEffect, useState } from 'react';
import { usePayrollStore } from '@/stores/payroll-store';
import { payrollAPI } from '@/lib/payroll-api';
import Link from 'next/link';

export default function PayrollPage() {
  const {
    payrollSummary,
    setPayrollSummary,
    loading,
    setLoading,
    error,
    setError,
    clearError,
  } = usePayrollStore();

  const [stats, setStats] = useState({
    totalRuns: 0,
    totalEmployees: 0,
    totalAmount: 0,
    pendingRuns: 0,
  });

  useEffect(() => {
    loadPayrollData();
  }, []);

  const loadPayrollData = async () => {
    try {
      setLoading(true);
      clearError();

      const summary = await payrollAPI.getPayrollSummary({ limit: 50 });
      setPayrollSummary(summary);

      // Calculate stats
      const totalRuns = summary.length;
      const totalEmployees = summary.reduce((acc, run) => acc + run.total_employees, 0);
      const totalAmount = summary.reduce((acc, run) => acc + run.total_net_amount, 0);
      const pendingRuns = summary.filter((run) => run.status === 'draft').length;

      setStats({
        totalRuns,
        totalEmployees,
        totalAmount,
        pendingRuns,
      });
    } catch (err: any) {
      setError(err.message || 'Error al cargar datos de payroll');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('ja-JP', {
      style: 'currency',
      currency: 'JPY',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ja-JP');
  };

  const getStatusBadge = (status: string) => {
    const statusMap = {
      draft: 'bg-gray-100 text-gray-800',
      calculated: 'bg-blue-100 text-blue-800',
      approved: 'bg-green-100 text-green-800',
      paid: 'bg-purple-100 text-purple-800',
      cancelled: 'bg-red-100 text-red-800',
    };

    const statusLabels = {
      draft: 'Borrador',
      calculated: 'Calculado',
      approved: 'Aprobado',
      paid: 'Pagado',
      cancelled: 'Cancelado',
    };

    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusMap[status as keyof typeof statusMap]}`}>
        {statusLabels[status as keyof typeof statusLabels] || status}
      </span>
    );
  };

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Sistema de Payroll</h1>
          <p className="text-gray-600 mt-2">
            Gestión completa de nóminas y cálculos salariales
          </p>
        </div>
        <Link
          href="/payroll/create"
          className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition-colors"
        >
          Nueva Ejecución de Payroll
        </Link>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg mb-6">
          <div className="flex justify-between items-center">
            <span>{error}</span>
            <button
              onClick={clearError}
              className="text-red-600 hover:text-red-800 font-medium"
            >
              Cerrar
            </button>
          </div>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
          <h3 className="text-sm font-medium text-gray-600 mb-2">Total de Ejecuciones</h3>
          <p className="text-3xl font-bold text-blue-600">{stats.totalRuns}</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
          <h3 className="text-sm font-medium text-gray-600 mb-2">Total de Empleados</h3>
          <p className="text-3xl font-bold text-green-600">{stats.totalEmployees}</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
          <h3 className="text-sm font-medium text-gray-600 mb-2">Monto Total Pagado</h3>
          <p className="text-2xl font-bold text-purple-600">{formatCurrency(stats.totalAmount)}</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
          <h3 className="text-sm font-medium text-gray-600 mb-2">Ejecuciones Pendientes</h3>
          <p className="text-3xl font-bold text-orange-600">{stats.pendingRuns}</p>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200 mb-8">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Acciones Rápidas</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            href="/payroll/calculate"
            className="flex items-center p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors"
          >
            <div className="flex-1">
              <h3 className="font-medium text-gray-900">Calcular Payroll Individual</h3>
              <p className="text-sm text-gray-600">Calcular salario para un empleado</p>
            </div>
          </Link>

          <Link
            href="/payroll/settings"
            className="flex items-center p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors"
          >
            <div className="flex-1">
              <h3 className="font-medium text-gray-900">Configuración</h3>
              <p className="text-sm text-gray-600">Ajustar tasas y parámetros</p>
            </div>
          </Link>

          <Link
            href="/payroll/timer-cards"
            className="flex items-center p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors"
          >
            <div className="flex-1">
              <h3 className="font-medium text-gray-900">Timer Cards</h3>
              <p className="text-sm text-gray-600">Subir y procesar timer cards</p>
            </div>
          </Link>
        </div>
      </div>

      {/* Payroll Summary Table */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">Resumen de Payroll</h2>
        </div>

        {loading ? (
          <div className="p-8 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="text-gray-600 mt-4">Cargando datos...</p>
          </div>
        ) : payrollSummary.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-gray-600">No hay ejecuciones de payroll registradas</p>
            <Link
              href="/payroll/create"
              className="mt-4 inline-block bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
            >
              Crear Primera Ejecución
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Período
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Estado
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Empleados
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Monto Bruto
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Monto Neto
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Acciones
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {payrollSummary.map((run) => (
                  <tr key={run.payroll_run_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {formatDate(run.pay_period_start)} - {formatDate(run.pay_period_end)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(run.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {run.total_employees}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatCurrency(run.total_gross_amount)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatCurrency(run.total_net_amount)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <Link
                        href={`/payroll/${run.payroll_run_id}`}
                        className="text-blue-600 hover:text-blue-900"
                      >
                        Ver Detalles
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
