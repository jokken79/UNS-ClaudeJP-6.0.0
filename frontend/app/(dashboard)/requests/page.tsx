'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  DocumentTextIcon,
  MagnifyingGlassIcon,
  UserIcon,
  CalendarDaysIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon
} from '@heroicons/react/24/outline';
import { requestService } from '@/lib/api';

interface Request {
  id: number;
  employee_id: number;
  employee_name?: string;
  request_type: string;
  status: string;
  start_date: string;
  end_date: string;
  total_days: number;
  reason?: string;
  notes?: string;
  reviewed_by?: number;
  reviewed_at?: string;
  review_notes?: string;
  created_at: string;
}

interface RequestsResponse {
  items: Request[];
  total: number;
}

export default function RequestsPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;

  const { data, isLoading } = useQuery<RequestsResponse>({
    queryKey: ['requests', searchTerm, statusFilter, typeFilter, currentPage],
    queryFn: async (): Promise<RequestsResponse> => {
      const params: any = {
        page: currentPage,
        page_size: pageSize,
      };
      if (searchTerm) params.search = searchTerm;
      if (statusFilter !== 'all') params.status = statusFilter;
      if (typeFilter !== 'all') params.request_type = typeFilter;
      const response = await requestService.getRequests<Request[]>(params);
      return {
        items: response,
        total: response.length,
      };
    },
  });

  const getRequestTypeLabel = (type: string) => {
    const types: Record<string, string> = {
      yukyu: '有給休暇',
      hankyu: '半休',
      ikkikokoku: '一時帰国',
      taisha: '退社'
    };
    return types[type] || type;
  };

  const getRequestTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      yukyu: 'bg-blue-100 text-blue-800',
      hankyu: 'bg-green-100 text-green-800',
      ikkikokoku: 'bg-purple-100 text-purple-800',
      taisha: 'bg-red-100 text-red-800'
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
  };

  const getStatusBadge = (status: string) => {
    const badges: Record<string, { bg: string; text: string; label: string; icon: any }> = {
      pending: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: '審査中', icon: ClockIcon },
      approved: { bg: 'bg-green-100', text: 'text-green-800', label: '承認済み', icon: CheckCircleIcon },
      rejected: { bg: 'bg-red-100', text: 'text-red-800', label: '却下', icon: XCircleIcon }
    };
    const badge = badges[status] || badges.pending;
    const Icon = badge.icon;

    return (
      <div className="flex items-center gap-1">
        <Icon className="h-4 w-4" />
        <span className={`px-2 py-1 text-xs rounded-full ${badge.bg} ${badge.text}`}>
          {badge.label}
        </span>
      </div>
    );
  };

  const requests = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / pageSize);

  // Count by status
  const pendingCount = requests.filter((r: Request) => r.status === 'pending').length;
  const approvedCount = requests.filter((r: Request) => r.status === 'approved').length;
  const rejectedCount = requests.filter((r: Request) => r.status === 'rejected').length;

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/20 p-4 sm:p-8">
      <div className="max-w-7xl mx-auto">

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-extrabold text-foreground">申請管理</h1>
          <p className="text-muted-foreground mt-1">従業員からの各種申請の管理・承認</p>
        </div>

        {/* Search and Filters */}
        <div className="bg-card rounded-xl shadow-sm border p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="relative">
              <MagnifyingGlassIcon className="h-5 w-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder="従業員名、IDで検索..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-input rounded-lg focus:ring-2 focus:ring-primary bg-background"
              />
            </div>

            <div>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="w-full px-3 py-2 border border-input rounded-lg focus:ring-2 focus:ring-primary bg-background"
              >
                <option value="all">全種類</option>
                <option value="yukyu">有給休暇</option>
                <option value="hankyu">半休</option>
                <option value="ikkikokoku">一時帰国</option>
                <option value="taisha">退社</option>
              </select>
            </div>

            <div>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full px-3 py-2 border border-input rounded-lg focus:ring-2 focus:ring-primary bg-background"
              >
                <option value="all">全ステータス</option>
                <option value="pending">審査中</option>
                <option value="approved">承認済み</option>
                <option value="rejected">却下</option>
              </select>
            </div>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-card rounded-xl shadow-sm border p-4">
            <p className="text-sm text-muted-foreground mb-1">審査中</p>
            <p className="text-3xl font-bold text-yellow-600">{pendingCount}</p>
          </div>
          <div className="bg-card rounded-xl shadow-sm border p-4">
            <p className="text-sm text-muted-foreground mb-1">承認済み</p>
            <p className="text-3xl font-bold text-green-600">{approvedCount}</p>
          </div>
          <div className="bg-card rounded-xl shadow-sm border p-4">
            <p className="text-sm text-muted-foreground mb-1">却下</p>
            <p className="text-3xl font-bold text-red-600">{rejectedCount}</p>
          </div>
        </div>

        {/* Results */}
        <div className="mb-4">
          <p className="text-muted-foreground">
            {total > 0 ? `${total}件中 ${(currentPage - 1) * pageSize + 1}-${Math.min(currentPage * pageSize, total)}件を表示` : '申請が見つかりませんでした'}
          </p>
        </div>

        {/* Requests List */}
        {isLoading ? (
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="bg-card rounded-xl shadow-sm border p-6 animate-pulse">
                <div className="flex justify-between mb-4">
                  <div className="h-6 bg-muted rounded w-1/3"></div>
                  <div className="h-6 bg-muted rounded w-20"></div>
                </div>
                <div className="space-y-2">
                  <div className="h-4 bg-muted rounded"></div>
                  <div className="h-4 bg-muted rounded w-5/6"></div>
                </div>
              </div>
            ))}
          </div>
        ) : requests.length === 0 ? (
          <div className="bg-card rounded-xl shadow-sm border p-12 text-center">
            <DocumentTextIcon className="h-16 w-16 text-muted-foreground/50 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-foreground mb-2">申請がありません</h3>
            <p className="text-muted-foreground">検索条件を変更してください</p>
          </div>
        ) : (
          <div className="space-y-4">
            {requests.map((request: Request) => (
              <div key={request.id} className="bg-card rounded-xl shadow-sm border hover:shadow-md transition-shadow">
                <div className="p-6">
                  {/* Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <UserIcon className="h-8 w-8 text-muted-foreground" />
                      <div>
                        <h3 className="font-semibold text-foreground text-lg">
                          {request.employee_name || `従業員ID: ${request.employee_id}`}
                        </h3>
                        <p className="text-sm text-muted-foreground">
                          申請日: {new Date(request.created_at).toLocaleDateString('ja-JP')}
                        </p>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      {getStatusBadge(request.status)}
                      <span className={`px-3 py-1 text-sm rounded-full font-medium ${getRequestTypeColor(request.request_type)}`}>
                        {getRequestTypeLabel(request.request_type)}
                      </span>
                    </div>
                  </div>

                  {/* Request Details */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                    <div className="flex items-center gap-2">
                      <CalendarDaysIcon className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <p className="text-xs text-muted-foreground">開始日</p>
                        <p className="text-sm font-medium text-foreground">
                          {new Date(request.start_date).toLocaleDateString('ja-JP')}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <CalendarDaysIcon className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <p className="text-xs text-muted-foreground">終了日</p>
                        <p className="text-sm font-medium text-foreground">
                          {new Date(request.end_date).toLocaleDateString('ja-JP')}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <ClockIcon className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <p className="text-xs text-muted-foreground">日数</p>
                        <p className="text-sm font-medium text-foreground">{request.total_days}日</p>
                      </div>
                    </div>
                  </div>

                  {/* Reason */}
                  {request.reason && (
                    <div className="mb-4">
                      <p className="text-xs text-muted-foreground mb-1">理由</p>
                      <p className="text-sm text-foreground bg-muted p-3 rounded-lg">{request.reason}</p>
                    </div>
                  )}

                  {/* Notes */}
                  {request.notes && (
                    <div className="mb-4">
                      <p className="text-xs text-muted-foreground mb-1">備考</p>
                      <p className="text-sm text-foreground bg-muted p-3 rounded-lg">{request.notes}</p>
                    </div>
                  )}

                  {/* Review Info */}
                  {request.status !== 'pending' && request.reviewed_at && (
                    <div className="pt-4 border-t border-border">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">
                          審査日: {new Date(request.reviewed_at).toLocaleDateString('ja-JP')}
                        </span>
                        {request.review_notes && (
                          <p className="text-muted-foreground italic">"{request.review_notes}"</p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="mt-6 flex justify-center">
            <nav className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="px-4 py-2 text-sm font-medium text-muted-foreground bg-card border border-input rounded-md hover:bg-accent hover:text-accent-foreground disabled:opacity-50"
              >
                前へ
              </button>

              {[...Array(Math.min(5, totalPages))].map((_, i) => {
                const page = Math.max(1, Math.min(totalPages, currentPage - 2 + i));
                return (
                  <button
                    key={page}
                    onClick={() => setCurrentPage(page)}
                    className={`px-4 py-2 text-sm font-medium rounded-md ${
                      page === currentPage
                        ? 'text-primary bg-primary/10 border border-primary/30'
                        : 'text-muted-foreground bg-card border border-input hover:bg-accent hover:text-accent-foreground'
                    }`}
                  >
                    {page}
                  </button>
                );
              })}

              <button
                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                disabled={currentPage === totalPages}
                className="px-4 py-2 text-sm font-medium text-muted-foreground bg-card border border-input rounded-md hover:bg-accent hover:text-accent-foreground disabled:opacity-50"
              >
                次へ
              </button>
            </nav>
          </div>
        )}
      </div>
    </div>
  );
}
