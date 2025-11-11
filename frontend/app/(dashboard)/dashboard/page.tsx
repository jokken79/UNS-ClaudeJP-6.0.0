'use client';

import { useAuthStore } from '@/stores/auth-store';
import { useQuery } from '@tanstack/react-query';
import { employeeService, candidateService, factoryService, timerCardService } from '@/lib/api';
import { MetricCard } from '@/components/dashboard/metric-card';
import { StatsChart } from '@/components/dashboard/stats-chart';
import { DashboardHeader } from '@/components/dashboard/dashboard-header';
import { AreaChartCard, EmployeeTrendChart, WorkHoursTrendChart, SalaryTrendChart } from '@/components/dashboard/charts/AreaChartCard';
import { BarChartCard, MonthlySalaryBarChart } from '@/components/dashboard/charts/BarChartCard';
import { DonutChartCard, EmployeeStatusDonutChart, NationalityDonutChart } from '@/components/dashboard/charts/DonutChartCard';
import { TrendCard, EmployeeTrendCard, HoursTrendCard, SalaryTrendCard, CandidatesTrendCard } from '@/components/dashboard/charts/TrendCard';
import { Users, UserCheck, Building2, Clock, UserPlus, FileCheck, AlertTriangle, DollarSign, TrendingUp, Home } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useEffect, useState } from 'react';
import { getAllDashboardData } from '@/lib/dashboard-data';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { PageSkeleton } from '@/components/page-skeleton';
import { ErrorState } from '@/components/error-state';
import { useDelayedLoading, useCombinedLoading, getErrorType } from '@/lib/loading-utils';

export default function DashboardPage() {
  const { isAuthenticated, user } = useAuthStore();
  const [mounted, setMounted] = useState(false);
  const [dashboardData, setDashboardData] = useState<ReturnType<typeof getAllDashboardData> | null>(null);

  // Ensure component is mounted before making API calls
  useEffect(() => {
    setMounted(true);
    // Load mock dashboard data
    setDashboardData(getAllDashboardData());
  }, []);

  // Fetch statistics with React Query - only if authenticated and mounted
  const { data: employeesData, isLoading: loadingEmployees, error: errorEmployees, refetch: refetchEmployees } = useQuery({
    queryKey: ['employees'],
    queryFn: () => employeeService.getEmployees(),
    enabled: isAuthenticated && mounted,
    retry: 1,
  });

  const { data: candidates, isLoading: loadingCandidates, error: errorCandidates, refetch: refetchCandidates } = useQuery({
    queryKey: ['candidates'],
    queryFn: () => candidateService.getCandidates(),
    enabled: isAuthenticated && mounted,
    retry: 1,
  });

  const { data: factories, isLoading: loadingFactories, error: errorFactories, refetch: refetchFactories } = useQuery({
    queryKey: ['factories'],
    queryFn: () => factoryService.getFactories(),
    enabled: isAuthenticated && mounted,
    retry: 1,
  });

  const { data: timerCards, isLoading: loadingTimerCards, error: errorTimerCards, refetch: refetchTimerCards } = useQuery({
    queryKey: ['timerCards'],
    queryFn: () => timerCardService.getTimerCards(),
    enabled: isAuthenticated && mounted,
    retry: 1,
  });

  // Safely access items from API responses
  const employeeItems = employeesData?.items || [];
  const candidateItems = Array.isArray(candidates) ? candidates : (candidates?.items || []);
  const factoryItems = factories || []; // factoryService.getFactories() returns Factory[] directly
  const timerCardItems = timerCards || []; // timerCardService.getTimerCards() returns TimerCard[] directly

  // Calculate statistics
  const stats = {
    totalCandidates: Array.isArray(candidateItems) ? candidateItems.length : 0,
    pendingCandidates: Array.isArray(candidateItems) ? candidateItems.filter((c: any) => c.status === 'pending' || c.status === 'pending_approval').length : 0,
    totalEmployees: Array.isArray(employeeItems) ? employeeItems.length : 0,
    activeEmployees: Array.isArray(employeeItems) ? employeeItems.filter((e: any) => e.status === 'active').length : 0,
    totalFactories: Array.isArray(factoryItems) ? factoryItems.length : 0,
    totalTimerCards: Array.isArray(timerCardItems) ? timerCardItems.length : 0,
    employeesInCorporateHousing: Array.isArray(employeeItems) ? employeeItems.filter((e: any) => e.is_corporate_housing === true).length : 0,
  };

  // Combined loading state for components that need it
  const isLoading = loadingEmployees || loadingCandidates || loadingFactories || loadingTimerCards;

  // Smart combined loading state with delay to prevent flashing (for page skeleton)
  const showLoading = useCombinedLoading(
    [loadingEmployees, loadingCandidates, loadingFactories, loadingTimerCards],
    { delay: 200, minDuration: 500 }
  );

  // Check for critical errors (all queries failed)
  const hasCriticalError = errorEmployees && errorCandidates && errorFactories && errorTimerCards;
  const firstError = errorEmployees || errorCandidates || errorFactories || errorTimerCards;

  // Refresh all data
  const handleRefresh = () => {
    refetchEmployees();
    refetchCandidates();
    refetchFactories();
    refetchTimerCards();
    setDashboardData(getAllDashboardData());
  };

  // Show loading state while mounting or authenticating
  if (!mounted) {
    return <PageSkeleton type="dashboard" />;
  }

  // Show authentication required message
  if (!isAuthenticated) {
    return (
      <ErrorState
        type="forbidden"
        title="Authentication Required"
        message="Please log in to access the dashboard."
        showRetry={false}
        showGoBack={false}
      />
    );
  }

  // Show loading skeleton with delay (prevents flashing on fast loads)
  if (showLoading) {
    return <PageSkeleton type="dashboard" />;
  }

  // Show error state if all queries failed
  if (hasCriticalError && firstError) {
    return (
      <ErrorState
        type={getErrorType(firstError)}
        title="Failed to Load Dashboard"
        message="Unable to fetch dashboard data. Please try again."
        details={firstError}
        onRetry={handleRefresh}
        showRetry={true}
        showGoBack={false}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Dashboard Header */}
      <DashboardHeader
        title="Dashboard"
        subtitle={`Bienvenido, ${user?.username || 'Usuario'}`}
        dateRange={{
          start: new Date(new Date().setDate(1)),
          end: new Date(),
        }}
        onRefresh={handleRefresh}
        onExport={() => console.log('Export')}
        onPrint={() => console.log('Print')}
        isRefreshing={isLoading}
      />

      {/* Hero Section - Welcome with Quick Stats Summary */}
      <Card className="bg-gradient-to-br from-primary/5 via-background to-background border-primary/20 hover:bg-accent hover:text-accent-foreground">
        <CardContent className="p-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
            <div className="flex-1">
              <h2 className="text-2xl font-bold mb-2">
                ¡Bienvenido de nuevo, {user?.username}! 👋
              </h2>
              <p className="text-muted-foreground">
                Aquí está un resumen de tu sistema de gestión de RRHH para hoy.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center">
                <div className="text-3xl font-bold text-primary">{stats.totalEmployees}</div>
                <div className="text-xs text-muted-foreground">Empleados</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-emerald-600">{stats.activeEmployees}</div>
                <div className="text-xs text-muted-foreground">Activos</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions Section */}
      <div>
        <h3 className="text-lg font-semibold mb-3">Acciones Rápidas</h3>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Button
            variant="outline"
            className="h-auto py-4 flex-col gap-2 hover:bg-accent hover:text-accent-foreground hover:border-primary"
            asChild
          >
            <a href="/employees/new">
              <UserPlus className="h-6 w-6 text-primary" />
              <span className="font-medium">Añadir Empleado</span>
            </a>
          </Button>
          <Button
            variant="outline"
            className="h-auto py-4 flex-col gap-2 hover:bg-accent hover:text-accent-foreground hover:border-blue-500"
            asChild
          >
            <a href="/timercards">
              <Clock className="h-6 w-6 text-blue-600" />
              <span className="font-medium">Ver タイムカード</span>
            </a>
          </Button>
          <Button
            variant="outline"
            className="h-auto py-4 flex-col gap-2 hover:bg-accent hover:text-accent-foreground hover:border-emerald-500"
            asChild
          >
            <a href="/candidates">
              <FileCheck className="h-6 w-6 text-emerald-600" />
              <span className="font-medium">Aprobar Candidatos</span>
            </a>
          </Button>
          <Button
            variant="outline"
            className="h-auto py-4 flex-col gap-2 hover:bg-accent hover:text-accent-foreground hover:border-amber-500"
            asChild
          >
            <a href="/salary">
              <DollarSign className="h-6 w-6 text-amber-600" />
              <span className="font-medium">Procesar Nómina</span>
            </a>
          </Button>
        </div>
      </div>

      {/* Metrics Grid - Bento Style with Mixed Sizes */}
      <div>
        <h3 className="text-lg font-semibold mb-3">Métricas Principales</h3>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            title="Total Candidatos"
            value={stats.totalCandidates}
            description={`${stats.pendingCandidates} pendientes de aprobación`}
            icon={Users}
            trend={{ value: 12, isPositive: true }}
            loading={isLoading}
            variant="default"
            theme="info"
          />
          <MetricCard
            title="Empleados Activos"
            value={stats.activeEmployees}
            description={`${stats.totalEmployees} total en sistema`}
            icon={UserCheck}
            trend={{ value: 8, isPositive: true }}
            loading={isLoading}
            variant="large"
            theme="success"
            className="md:col-span-1 lg:col-span-2 md:row-span-2"
          />
          <MetricCard
            title="Fábricas Activas"
            value={stats.totalFactories}
            description="Clientes en operación"
            icon={Building2}
            trend={{ value: 3, isPositive: true }}
            loading={isLoading}
            variant="default"
            theme="default"
          />
          <MetricCard
            title="社宅利用者"
            value={stats.employeesInCorporateHousing}
            description="Corporate Housing"
            icon={Home}
            trend={{ value: 0, isPositive: true }}
            loading={isLoading}
            variant="compact"
            theme="default"
          />
          <MetricCard
            title="Asistencias (Mes)"
            value={stats.totalTimerCards}
            description="Registros de タイムカード"
            icon={Clock}
            trend={{ value: 5, isPositive: false }}
            loading={isLoading}
            variant="compact"
            theme="warning"
          />
        </div>
      </div>

      {/* Trend Cards Row */}
      <div>
        <h3 className="text-lg font-semibold mb-3">Tendencias</h3>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <EmployeeTrendCard
            value={dashboardData?.stats.current.totalEmployees || 0}
            previousValue={dashboardData?.stats.previous.totalEmployees}
            loading={isLoading}
          />
          <HoursTrendCard
            value={dashboardData?.stats.current.totalHours || 0}
            previousValue={dashboardData?.stats.previous.totalHours}
            loading={isLoading}
          />
          <SalaryTrendCard
            value={dashboardData?.stats.current.totalSalary || 0}
            previousValue={dashboardData?.stats.previous.totalSalary}
            loading={isLoading}
          />
          <CandidatesTrendCard
            value={dashboardData?.stats.current.totalCandidates || 0}
            previousValue={dashboardData?.stats.previous.totalCandidates}
            loading={isLoading}
          />
        </div>
      </div>

      {/* Charts Section - Bento Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        {/* Main Chart - Larger */}
        <div className="lg:col-span-4">
          <StatsChart
            data={dashboardData?.timeSeries}
            showPeriodSelector={true}
            showExportButton={true}
          />
        </div>

        {/* Donut Chart */}
        <div className="lg:col-span-3">
          <EmployeeStatusDonutChart
            data={dashboardData?.distribution.byStatus || []}
            loading={isLoading}
          />
        </div>
      </div>

      {/* Second Row Charts */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <NationalityDonutChart
          data={dashboardData?.distribution.byNationality || []}
          loading={isLoading}
        />
        <div className="lg:col-span-2">
          <MonthlySalaryBarChart
            data={(dashboardData?.timeSeries || []) as any}
            loading={isLoading}
          />
        </div>
      </div>

      {/* Recent Activity & Upcoming Items */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Recent Activity Timeline */}
        <Card>
          <CardHeader>
            <CardTitle>Actividad Reciente</CardTitle>
            <CardDescription>Últimas acciones en el sistema</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {isLoading ? (
                <div className="text-sm text-muted-foreground">Cargando...</div>
              ) : dashboardData?.recentActivity && dashboardData.recentActivity.length > 0 ? (
                dashboardData.recentActivity.slice(0, 8).map((activity, index) => (
                  <motion.div
                    key={activity.id}
                    className="flex items-start gap-3 border-l-2 border-primary/20 pl-4 pb-4 last:pb-0 last:border-l-0"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    <div className="mt-1 h-2 w-2 rounded-full bg-primary" />
                    <div className="flex-1">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm">
                          <span className="font-medium">{activity.user}</span>{' '}
                          <span className="text-muted-foreground">{activity.description}</span>
                        </p>
                        <span className="text-xs text-muted-foreground whitespace-nowrap">
                          {format(new Date(activity.timestamp), 'HH:mm', { locale: es })}
                        </span>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {format(new Date(activity.timestamp), 'dd MMM yyyy', { locale: es })}
                      </span>
                    </div>
                  </motion.div>
                ))
              ) : (
                <div className="text-sm text-muted-foreground text-center py-8">
                  No hay actividad reciente
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Upcoming Items / Alerts */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-600" />
              Elementos Pendientes
            </CardTitle>
            <CardDescription>Acciones que requieren atención</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {isLoading ? (
                <div className="text-sm text-muted-foreground">Cargando...</div>
              ) : dashboardData?.upcomingItems && dashboardData.upcomingItems.length > 0 ? (
                dashboardData.upcomingItems.slice(0, 6).map((item, index) => {
                  const priorityColors = {
                    high: 'border-l-red-500 bg-red-50/50 dark:bg-red-950/20',
                    medium: 'border-l-amber-500 bg-amber-50/50 dark:bg-amber-950/20',
                    low: 'border-l-blue-500 bg-blue-50/50 dark:bg-blue-950/20',
                  };

                  return (
                    <motion.div
                      key={item.id}
                      className={cn(
                        'p-3 rounded-lg border-l-4',
                        priorityColors[item.priority]
                      )}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <p className="font-medium text-sm">{item.title}</p>
                          <p className="text-xs text-muted-foreground">{item.description}</p>
                        </div>
                        <span className="text-xs text-muted-foreground whitespace-nowrap">
                          {format(item.dueDate, 'dd MMM', { locale: es })}
                        </span>
                      </div>
                    </motion.div>
                  );
                })
              ) : (
                <div className="text-sm text-muted-foreground text-center py-8">
                  No hay elementos pendientes
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Candidates */}
      <Card>
        <CardHeader>
          <CardTitle>Candidatos Recientes</CardTitle>
          <CardDescription>Últimos registros de 履歴書</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {isLoading ? (
              <div className="text-sm text-muted-foreground">Cargando...</div>
            ) : candidateItems.length > 0 ? (
              candidateItems.slice(0, 5).map((candidate: any) => (
                <div key={candidate.id} className="flex items-center justify-between border-b pb-2 last:border-0">
                  <div>
                    <p className="font-medium text-sm">
                      {candidate.name || `${candidate.first_name || ''} ${candidate.last_name || ''}`.trim() || 'Sin nombre'}
                    </p>
                    <p className="text-xs text-muted-foreground">{candidate.status || 'pendiente'}</p>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {candidate.created_at ? format(new Date(candidate.created_at), 'dd MMM yyyy', { locale: es }) : '-'}
                  </span>
                </div>
              ))
            ) : (
              <div className="text-sm text-muted-foreground text-center py-4">
                No hay candidatos recientes
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
