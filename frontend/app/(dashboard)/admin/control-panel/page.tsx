'use client';

// Disable static generation for this page (uses client-side hooks)
export const dynamic = 'force-dynamic';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Settings,
  Eye,
  EyeOff,
  Activity,
  PieChart,
  Download,
  Upload,
  Shield,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Wrench,
  Users,
  UserCog,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { useAllPagesVisibility } from '@/hooks/use-page-visibility';
import api from '@/lib/api';
import { UnderConstruction } from '@/components/ui/under-construction';

interface Statistics {
  pages: {
    total: number;
    enabled: number;
    disabled: number;
    percentage_enabled: number;
  };
  system: {
    maintenance_mode: boolean;
    recent_changes_24h: number;
  };
}

interface RolePermission {
  role_key: string;
  page_key: string;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

interface RolePermissionsResponse {
  role_key: string;
  permissions: RolePermission[];
  total_pages: number;
  enabled_pages: number;
}

const ROLES = [
  { key: 'ADMIN', name: 'アドミニストレーター', name_en: 'Administrator', description: 'Acceso completo a todas las funciones' },
  { key: 'KEITOSAN', name: '経理管理', name_en: 'Finance Manager', description: 'Acceso a finanzas y contabilidad' },
  { key: 'TANTOSHA', name: '担当者', name_en: 'Representative', description: 'Acceso a RRHH y operaciones' },
  { key: 'EMPLOYEE', name: '従業員', name_en: 'Employee', description: 'Acceso limitado a datos propios' },
];

export default function AdminControlPanelPage() {
  const { pages, loading: pagesLoading, updatePageVisibility } = useAllPagesVisibility();
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [statisticsLoading, setStatisticsLoading] = useState(true);
  const [bulkActionLoading, setBulkActionLoading] = useState(false);
  const [rolePermissions, setRolePermissions] = useState<Record<string, RolePermissionsResponse>>({});
  const [roleLoading, setRoleLoading] = useState<Record<string, boolean>>({});
  const [activeTab, setActiveTab] = useState('global');

  const fetchStatistics = async () => {
    try {
      setStatisticsLoading(true);
      const response = await api.get('/admin/statistics');
      setStatistics(response.data);
    } catch (error: any) {
      console.error('Error fetching statistics:', error);
      toast.error('Failed to fetch statistics');
    } finally {
      setStatisticsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatistics();
  }, []);

  const fetchRolePermissions = async (roleKey: string) => {
    try {
      setRoleLoading(prev => ({ ...prev, [roleKey]: true }));
      const response = await api.get(`/role-permissions/${roleKey}`);
      setRolePermissions(prev => ({
        ...prev,
        [roleKey]: response.data
      }));
    } catch (error: any) {
      console.error(`Error fetching permissions for role ${roleKey}:`, error);
      toast.error(`Failed to fetch permissions for role ${roleKey}`);
    } finally {
      setRoleLoading(prev => ({ ...prev, [roleKey]: false }));
    }
  };

  const handleRoleToggle = async (roleKey: string, pageKey: string, currentState: boolean) => {
    try {
      await api.put(`/role-permissions/${roleKey}/${pageKey}`, {
        is_enabled: !currentState
      });
      toast.success(`Permission updated for ${roleKey} - ${pageKey}`);

      // Update local state
      await fetchRolePermissions(roleKey);
    } catch (error: any) {
      console.error('Error updating permission:', error);
      toast.error('Failed to update permission');
    }
  };

  const handleBulkRoleEnable = async (roleKey: string) => {
    try {
      setRoleLoading(prev => ({ ...prev, [roleKey]: true }));
      const roleData = rolePermissions[roleKey];
      if (!roleData) return;

      const disabledPages = roleData.permissions.filter(p => !p.is_enabled);
      if (disabledPages.length === 0) {
        toast.info('All pages are already enabled for this role');
        return;
      }

      await api.post(`/role-permissions/bulk-update/${roleKey}`, {
        permissions: disabledPages.map(p => ({
          page_key: p.page_key,
          is_enabled: true
        }))
      });

      toast.success(`Enabled ${disabledPages.length} pages for ${roleKey}`);
      await fetchRolePermissions(roleKey);
    } catch (error: any) {
      console.error('Error enabling pages:', error);
      toast.error('Failed to enable pages');
    } finally {
      setRoleLoading(prev => ({ ...prev, [roleKey]: false }));
    }
  };

  const handleBulkRoleDisable = async (roleKey: string) => {
    try {
      setRoleLoading(prev => ({ ...prev, [roleKey]: true }));
      const roleData = rolePermissions[roleKey];
      if (!roleData) return;

      const enabledPages = roleData.permissions.filter(p => p.is_enabled);
      if (enabledPages.length === 0) {
        toast.info('All pages are already disabled for this role');
        return;
      }

      await api.post(`/role-permissions/bulk-update/${roleKey}`, {
        permissions: enabledPages.map(p => ({
          page_key: p.page_key,
          is_enabled: false
        }))
      });

      toast.success(`Disabled ${enabledPages.length} pages for ${roleKey}`);
      await fetchRolePermissions(roleKey);
    } catch (error: any) {
      console.error('Error disabling pages:', error);
      toast.error('Failed to disable pages');
    } finally {
      setRoleLoading(prev => ({ ...prev, [roleKey]: false }));
    }
  };

  const handleToggle = async (pageKey: string, currentState: boolean) => {
    try {
      await updatePageVisibility(pageKey, !currentState);
      toast.success(`Page ${!currentState ? 'enabled' : 'disabled'} successfully`);
      fetchStatistics(); // Refresh statistics
    } catch (error: any) {
      toast.error('Failed to update page visibility');
    }
  };

  const handleBulkEnable = async () => {
    try {
      setBulkActionLoading(true);
      const disabledPages = pages.filter(p => !p.is_enabled);
      await api.post('/admin/pages/bulk-toggle', {
        page_keys: disabledPages.map(p => p.page_key),
        is_enabled: true,
      });
      toast.success(`Enabled ${disabledPages.length} pages`);
      window.location.reload();
    } catch (error: any) {
      toast.error('Failed to enable pages');
    } finally {
      setBulkActionLoading(false);
    }
  };

  const handleBulkDisable = async () => {
    try {
      setBulkActionLoading(true);
      const enabledPages = pages.filter(p => p.is_enabled);
      await api.post('/admin/pages/bulk-toggle', {
        page_keys: enabledPages.map(p => p.page_key),
        is_enabled: false,
      });
      toast.success(`Disabled ${enabledPages.length} pages`);
      window.location.reload();
    } catch (error: any) {
      toast.error('Failed to disable pages');
    } finally {
      setBulkActionLoading(false);
    }
  };

  const handleExportConfig = async () => {
    try {
      const response = await api.get('/admin/export-config');
      const dataStr = JSON.stringify(response.data, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(dataBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `uns-control-panel-config-${new Date().toISOString().split('T')[0]}.json`;
      link.click();
      URL.revokeObjectURL(url);
      toast.success('Configuration exported successfully');
    } catch (error: any) {
      toast.error('Failed to export configuration');
    }
  };

  if (pagesLoading || statisticsLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <RefreshCw className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Settings className="h-8 w-8" />
            Panel de Control Administrativo
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Gestiona qué módulos y páginas están visibles para los usuarios por rol
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleExportConfig} variant="outline" className="gap-2">
            <Download className="h-4 w-4" />
            Exportar Config
          </Button>
        </div>
      </div>

      {/* Statistics Cards */}
      {statistics && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total de Páginas
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.pages.total}</div>
              <p className="text-xs text-muted-foreground mt-1">
                Páginas registradas
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Páginas Habilitadas
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {statistics.pages.enabled}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {statistics.pages.percentage_enabled}% del total
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Páginas Deshabilitadas
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {statistics.pages.disabled}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Mostrando "En construcción"
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Cambios Recientes
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">
                {statistics.system.recent_changes_24h}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Últimas 24 horas
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="global" className="gap-2">
            <Settings className="h-4 w-4" />
            Global
          </TabsTrigger>
          {ROLES.map(role => (
            <TabsTrigger key={role.key} value={role.key} className="gap-2">
              {role.key === 'ADMIN' && <Shield className="h-4 w-4" />}
              {role.key === 'KEITOSAN' && <PieChart className="h-4 w-4" />}
              {role.key === 'TANTOSHA' && <Users className="h-4 w-4" />}
              {role.key === 'EMPLOYEE' && <UserCog className="h-4 w-4" />}
              {role.key}
            </TabsTrigger>
          ))}
        </TabsList>

        {/* Global Tab */}
        <TabsContent value="global" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Wrench className="h-5 w-5" />
                Acciones en Lote (Global)
              </CardTitle>
              <CardDescription>
                Habilita o deshabilita múltiples páginas globalmente
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-4">
                <Button
                  onClick={handleBulkEnable}
                  disabled={bulkActionLoading}
                  variant="outline"
                  className="gap-2"
                >
                  <CheckCircle className="h-4 w-4" />
                  Habilitar Todas
                </Button>
                <Button
                  onClick={handleBulkDisable}
                  disabled={bulkActionLoading}
                  variant="outline"
                  className="gap-2"
                >
                  <AlertTriangle className="h-4 w-4" />
                  Deshabilitar Todas
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <PieChart className="h-5 w-5" />
                Control de Páginas (Global)
              </CardTitle>
              <CardDescription>
                Activa o desactiva módulos específicos para todos los usuarios
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {pages.map((page, index) => (
                  <motion.div
                    key={page.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent/50 transition-colors">
                      <div className="flex-1">
                        <div className="flex items-center gap-3">
                          <h3 className="font-semibold">{page.page_name}</h3>
                          <Badge variant="secondary" className="text-xs">
                            {page.page_name_en}
                          </Badge>
                          {page.is_enabled ? (
                            <Badge variant="default" className="bg-green-600">
                              <Eye className="h-3 w-3 mr-1" />
                              Habilitado
                            </Badge>
                          ) : (
                            <Badge variant="destructive">
                              <EyeOff className="h-3 w-3 mr-1" />
                              Deshabilitado
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          {page.description || 'Sin descripción'}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          Ruta: {page.path}
                        </p>
                      </div>
                      <div className="flex items-center gap-4">
                        <Switch
                          checked={page.is_enabled}
                          onCheckedChange={() => handleToggle(page.page_key, page.is_enabled)}
                        />
                      </div>
                    </div>
                    {index < pages.length - 1 && <Separator className="mt-4" />}
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Role Tabs */}
        {ROLES.map(role => (
          <TabsContent key={role.key} value={role.key} className="space-y-6">
            {/* Role Header */}
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold flex items-center gap-2">
                  {role.key === 'ADMIN' && <Shield className="h-6 w-6" />}
                  {role.key === 'KEITOSAN' && <PieChart className="h-6 w-6" />}
                  {role.key === 'TANTOSHA' && <Users className="h-6 w-6" />}
                  {role.key === 'EMPLOYEE' && <UserCog className="h-6 w-6" />}
                  {role.name}
                </h2>
                <p className="text-sm text-muted-foreground mt-1">
                  {role.description}
                </p>
              </div>
            </div>

            {/* Role Statistics */}
            {rolePermissions[role.key] && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      Total Páginas
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{rolePermissions[role.key].total_pages}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      Habilitadas
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-green-600">
                      {rolePermissions[role.key].enabled_pages}
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      Deshabilitadas
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-red-600">
                      {rolePermissions[role.key].total_pages - rolePermissions[role.key].enabled_pages}
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Role Bulk Actions */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Wrench className="h-5 w-5" />
                  Acciones en Lote para {role.key}
                </CardTitle>
                <CardDescription>
                  Habilita o deshabilita múltiples páginas para este rol
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex gap-4">
                  <Button
                    onClick={() => handleBulkRoleEnable(role.key)}
                    disabled={roleLoading[role.key]}
                    variant="outline"
                    className="gap-2"
                  >
                    <CheckCircle className="h-4 w-4" />
                    Habilitar Todas
                  </Button>
                  <Button
                    onClick={() => handleBulkRoleDisable(role.key)}
                    disabled={roleLoading[role.key]}
                    variant="outline"
                    className="gap-2"
                  >
                    <AlertTriangle className="h-4 w-4" />
                    Deshabilitar Todas
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Role Permissions List */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Permisos de Acceso - {role.key}
                </CardTitle>
                <CardDescription>
                  Controla qué páginas puede ver este rol
                </CardDescription>
              </CardHeader>
              <CardContent>
                {!rolePermissions[role.key] && !roleLoading[role.key] && (
                  <Button
                    onClick={() => fetchRolePermissions(role.key)}
                    variant="outline"
                    className="gap-2"
                  >
                    <RefreshCw className="h-4 w-4" />
                    Cargar Permisos
                  </Button>
                )}

                {roleLoading[role.key] && (
                  <div className="flex items-center justify-center py-8">
                    <RefreshCw className="h-6 w-6 animate-spin text-primary" />
                  </div>
                )}

                {rolePermissions[role.key] && (
                  <div className="space-y-4">
                    {rolePermissions[role.key].permissions.map((permission, index) => (
                      <motion.div
                        key={permission.page_key}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.05 }}
                      >
                        <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent/50 transition-colors">
                          <div className="flex-1">
                            <div className="flex items-center gap-3">
                              <h3 className="font-semibold capitalize">{permission.page_key.replace('_', ' ')}</h3>
                              {permission.is_enabled ? (
                                <Badge variant="default" className="bg-green-600">
                                  <Eye className="h-3 w-3 mr-1" />
                                  Puede ver
                                </Badge>
                              ) : (
                                <Badge variant="destructive">
                                  <EyeOff className="h-3 w-3 mr-1" />
                                  No puede ver
                                </Badge>
                              )}
                            </div>
                            <p className="text-xs text-muted-foreground mt-1">
                              Última actualización: {permission.updated_at ? new Date(permission.updated_at).toLocaleString() : 'Nunca'}
                            </p>
                          </div>
                          <div className="flex items-center gap-4">
                            <Switch
                              checked={permission.is_enabled}
                              onCheckedChange={() => handleRoleToggle(role.key, permission.page_key, permission.is_enabled)}
                            />
                          </div>
                        </div>
                        {index < rolePermissions[role.key].permissions.length - 1 && <Separator className="mt-4" />}
                      </motion.div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        ))}
      </Tabs>

      {/* System Information */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Información del Sistema
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-sm">
            <strong>Modo Mantenimiento:</strong>{' '}
            {statistics?.system.maintenance_mode ? (
              <Badge variant="destructive">Activo</Badge>
            ) : (
              <Badge variant="default" className="bg-green-600">Inactivo</Badge>
            )}
          </p>
          <p className="text-sm text-muted-foreground">
            Las páginas deshabilitadas mostrarán una página de "En construcción" a los usuarios
          </p>
          <p className="text-sm text-muted-foreground">
            Los permisos por rol permiten control granular sobre qué páginas puede ver cada tipo de usuario
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
