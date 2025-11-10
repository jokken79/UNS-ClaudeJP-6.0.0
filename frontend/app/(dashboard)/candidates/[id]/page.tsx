'use client';

import { useParams, useRouter } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { CandidateEvaluator } from '@/components/CandidateEvaluator';
import {
  ArrowLeftIcon,
  PencilIcon,
  UserCircleIcon,
  PhoneIcon,
  IdentificationIcon,
  DocumentTextIcon,
  GlobeAltIcon,
  CalendarIcon,
  BriefcaseIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline';
import { candidateService } from '@/lib/api';

interface Candidate {
  id: number;
  rirekisho_id?: string;
  full_name_kanji?: string;
  full_name_kana?: string;
  full_name_roman?: string;
  date_of_birth?: string;
  age?: number;
  gender?: string;
  nationality?: string;
  phone?: string;
  mobile?: string;
  email?: string;
  postal_code?: string;
  current_address?: string;
  address?: string;
  address_banchi?: string;
  address_building?: string;
  status?: string;
  photo_url?: string;
  photo_data_url?: string;

  // Visa/Residence
  residence_status?: string;
  visa_period?: string;
  residence_expiry?: string;
  residence_card_number?: string;
  passport_number?: string;
  passport_expiry?: string;
  license_number?: string;
  license_expiry?: string;

  // Japanese Language
  listening_level?: string;
  speaking_level?: string;
  reading_level?: string;
  writing_level?: string;

  // Work Experience
  exp_nc_lathe?: boolean;
  exp_lathe?: boolean;
  exp_press?: boolean;
  exp_forklift?: boolean;
  exp_packing?: boolean;
  exp_welding?: boolean;
  exp_car_assembly?: boolean;
  exp_car_line?: boolean;
  exp_car_inspection?: boolean;
  exp_electronic_inspection?: boolean;
  exp_food_processing?: boolean;
  exp_casting?: boolean;
  exp_line_leader?: boolean;
  exp_painting?: boolean;
  exp_other?: string;

  // Emergency Contact
  emergency_contact_name?: string;
  emergency_contact_relation?: string;
  emergency_contact_phone?: string;

  // System
  created_at?: string;
  updated_at?: string;
}

export default function CandidateDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const id = params?.id as string;

  const { data: candidate, isLoading, error } = useQuery<Candidate>({
    queryKey: ['candidate', id],
    queryFn: () => candidateService.getCandidate(id),
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-background to-muted/20 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
          <p className="mt-4 text-muted-foreground">読み込み中...</p>
        </div>
      </div>
    );
  }

  if (error || !candidate) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-background to-muted/20 flex items-center justify-center">
        <div className="text-center">
          <ExclamationTriangleIcon className="h-16 w-16 text-destructive mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-foreground mb-2">候補者が見つかりません</h2>
          <p className="text-muted-foreground mb-6">指定された候補者は存在しないか、アクセス権限がありません。</p>
          <button
            onClick={() => router.push('/candidates')}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-primary-foreground bg-primary hover:bg-primary/90"
          >
            <ArrowLeftIcon className="h-5 w-5 mr-2" />
            候補者一覧に戻る
          </button>
        </div>
      </div>
    );
  }

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      pending: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: '審査中' },
      approved: { bg: 'bg-green-100', text: 'text-green-800', label: '承認済み' },
      rejected: { bg: 'bg-red-100', text: 'text-red-800', label: '却下' },
      hired: { bg: 'bg-blue-100', text: 'text-blue-800', label: '採用済み' }
    };
    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending;
    return (
      <span className={`px-3 py-1 text-sm rounded-full font-medium ${config.bg} ${config.text}`}>
        {config.label}
      </span>
    );
  };

  const experienceFields = [
    { key: 'exp_nc_lathe', label: 'NC旋盤' },
    { key: 'exp_lathe', label: '旋盤' },
    { key: 'exp_press', label: 'プレス' },
    { key: 'exp_forklift', label: 'フォークリフト' },
    { key: 'exp_packing', label: '梱包' },
    { key: 'exp_welding', label: '溶接' },
    { key: 'exp_car_assembly', label: '車部品組立' },
    { key: 'exp_car_line', label: '車部品ライン' },
    { key: 'exp_car_inspection', label: '車部品検査' },
    { key: 'exp_electronic_inspection', label: '電子部品検査' },
    { key: 'exp_food_processing', label: '食品加工' },
    { key: 'exp_casting', label: '鋳造' },
    { key: 'exp_line_leader', label: 'ラインリーダー' },
    { key: 'exp_painting', label: '塗装' },
  ];

  const hasExperience = experienceFields.some(field => candidate[field.key as keyof Candidate]);

  // Check if visa is expiring soon (within 90 days)
  const isVisaExpiringSoon = candidate.residence_expiry &&
    new Date(candidate.residence_expiry) < new Date(Date.now() + 90 * 24 * 60 * 60 * 1000);

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/20 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto">

        {/* Header */}
        <div className="mb-8 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push('/candidates')}
              className="p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors"
            >
              <ArrowLeftIcon className="h-6 w-6" />
            </button>
            <div>
              <h1 className="text-3xl font-bold text-foreground">候補者詳細</h1>
              <p className="text-muted-foreground mt-1">ID: {candidate.rirekisho_id || candidate.id}</p>
            </div>
          </div>

          <button
            onClick={() => router.push(`/candidates/${id}/edit`)}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-primary-foreground bg-primary hover:bg-primary/90 transition-colors shadow-sm"
          >
            <PencilIcon className="h-5 w-5 mr-2" />
            編集
          </button>
        </div>

        {/* Visa Warning */}
        {isVisaExpiringSoon && (
          <div className="mb-6 bg-yellow-50 dark:bg-yellow-900/20 border-l-4 border-yellow-400 dark:border-yellow-600 p-4 rounded-r-lg">
            <div className="flex">
              <ExclamationTriangleIcon className="h-6 w-6 text-yellow-600 dark:text-yellow-400 mr-3" />
              <div>
                <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-300">在留期間満了が近づいています</h3>
                <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
                  在留期限: {new Date(candidate.residence_expiry!).toLocaleDateString('ja-JP')}
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Left Column - Photo and Basic Info */}
          <div className="lg:col-span-1">
            {/* Photo Card */}
            <div className="bg-card rounded-2xl shadow-sm border border-input p-6 mb-6">
              <div className="flex flex-col items-center">
                <div className="w-32 h-32 bg-gradient-to-br from-primary/10 to-primary/20 rounded-full flex items-center justify-center overflow-hidden mb-4">
                  {(candidate.photo_data_url || candidate.photo_url) ? (
                    <img
                      src={candidate.photo_data_url || candidate.photo_url}
                      alt="候補者写真"
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <UserCircleIcon className="h-20 w-20 text-gray-400" />
                  )}
                </div>

                <h2 className="text-2xl font-bold text-foreground text-center mb-1">
                  {candidate.full_name_kanji || candidate.full_name_roman || '名前未設定'}
                </h2>

                {candidate.full_name_kana && (
                  <p className="text-muted-foreground mb-2">{candidate.full_name_kana}</p>
                )}

                {candidate.full_name_roman && (
                  <p className="text-muted-foreground text-sm mb-4">{candidate.full_name_roman}</p>
                )}

                <div className="mb-4">
                  {getStatusBadge(candidate.status || 'pending')}
                </div>
              </div>
            </div>

            {/* Quick Info Card */}
            <div className="bg-card rounded-2xl shadow-sm border border-input p-6">
              <h3 className="text-lg font-semibold text-foreground mb-4">基本情報</h3>
              <div className="space-y-3">
                {candidate.age && (
                  <div className="flex items-start gap-3">
                    <CalendarIcon className="h-5 w-5 text-gray-400 mt-0.5" />
                    <div>
                      <p className="text-sm text-muted-foreground">年齢</p>
                      <p className="text-foreground font-medium">{candidate.age}歳</p>
                    </div>
                  </div>
                )}

                {candidate.gender && (
                  <div className="flex items-start gap-3">
                    <UserCircleIcon className="h-5 w-5 text-gray-400 mt-0.5" />
                    <div>
                      <p className="text-sm text-muted-foreground">性別</p>
                      <p className="text-foreground font-medium">{candidate.gender}</p>
                    </div>
                  </div>
                )}

                {candidate.nationality && (
                  <div className="flex items-start gap-3">
                    <GlobeAltIcon className="h-5 w-5 text-gray-400 mt-0.5" />
                    <div>
                      <p className="text-sm text-muted-foreground">国籍</p>
                      <p className="text-foreground font-medium">{candidate.nationality}</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Quick Evaluation Card */}
            <CandidateEvaluator
              candidateId={candidate.id}
              candidateName={candidate.full_name_kanji || 'Candidate'}
              onSuccess={() => {
                // Refetch candidate data to update status
                queryClient.invalidateQueries({ queryKey: ['candidate', id] });
              }}
            />
          </div>

          {/* Right Column - Detailed Info */}
          <div className="lg:col-span-2 space-y-6">

            {/* Contact Information */}
            <div className="bg-card rounded-2xl shadow-sm border border-input p-6">
              <div className="flex items-center gap-2 mb-4">
                <div className="p-2 bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg">
                  <PhoneIcon className="h-5 w-5 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-foreground">連絡先情報</h3>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {candidate.phone && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">電話番号</p>
                    <p className="text-foreground">{candidate.phone}</p>
                  </div>
                )}

                {candidate.mobile && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">携帯電話</p>
                    <p className="text-foreground">{candidate.mobile}</p>
                  </div>
                )}

                {candidate.email && (
                  <div className="md:col-span-2">
                    <p className="text-sm text-muted-foreground mb-1">メールアドレス</p>
                    <p className="text-foreground">{candidate.email}</p>
                  </div>
                )}

                {(candidate.current_address || candidate.address || candidate.address_banchi || candidate.address_building) && (
                  <div className="md:col-span-2">
                    <p className="text-sm text-gray-500 mb-1">住所</p>
                    {candidate.current_address && (
                      <p className="text-gray-900">
                        <span className="text-xs text-muted-foreground">現住所: </span>
                        {candidate.current_address}
                      </p>
                    )}
                    {candidate.address_banchi && (
                      <p className="text-gray-900">
                        <span className="text-xs text-muted-foreground">番地: </span>
                        {candidate.address_banchi}
                      </p>
                    )}
                    {candidate.address_building && (
                      <p className="text-gray-900">
                        <span className="text-xs text-muted-foreground">物件名: </span>
                        {candidate.address_building}
                      </p>
                    )}
                    {!candidate.current_address && !candidate.address_banchi && !candidate.address_building && candidate.address && (
                      <p className="text-gray-900">{candidate.address}</p>
                    )}
                    {candidate.postal_code && (
                      <p className="text-sm text-gray-600 mt-1">〒 {candidate.postal_code}</p>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Visa/Residence Information */}
            <div className="bg-card rounded-2xl shadow-sm border border-input p-6">
              <div className="flex items-center gap-2 mb-4">
                <div className="p-2 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg">
                  <IdentificationIcon className="h-5 w-5 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-foreground">在留資格・書類情報</h3>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {candidate.residence_status && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">在留資格</p>
                    <p className="text-foreground font-medium">{candidate.residence_status}</p>
                  </div>
                )}

                {candidate.visa_period && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">在留期間</p>
                    <p className="text-foreground">{candidate.visa_period}</p>
                  </div>
                )}

                {candidate.residence_expiry && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">在留期間満了日</p>
                    <p className={`font-medium ${isVisaExpiringSoon ? 'text-yellow-600' : 'text-foreground'}`}>
                      {new Date(candidate.residence_expiry).toLocaleDateString('ja-JP')}
                    </p>
                  </div>
                )}

                {candidate.residence_card_number && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">在留カード番号</p>
                    <p className="text-foreground font-mono">{candidate.residence_card_number}</p>
                  </div>
                )}

                {candidate.passport_number && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">パスポート番号</p>
                    <p className="text-foreground font-mono">{candidate.passport_number}</p>
                  </div>
                )}

                {candidate.passport_expiry && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">パスポート期限</p>
                    <p className="text-foreground">{new Date(candidate.passport_expiry).toLocaleDateString('ja-JP')}</p>
                  </div>
                )}

                {candidate.license_number && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">運転免許証番号</p>
                    <p className="text-foreground font-mono">{candidate.license_number}</p>
                  </div>
                )}

                {candidate.license_expiry && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">運転免許期限</p>
                    <p className="text-foreground">{new Date(candidate.license_expiry).toLocaleDateString('ja-JP')}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Japanese Language Skills */}
            {(candidate.listening_level || candidate.speaking_level || candidate.reading_level || candidate.writing_level) && (
              <div className="bg-card rounded-2xl shadow-sm border border-input p-6">
                <div className="flex items-center gap-2 mb-4">
                  <div className="p-2 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg">
                    <DocumentTextIcon className="h-5 w-5 text-white" />
                  </div>
                  <h3 className="text-lg font-semibold text-foreground">日本語能力</h3>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {candidate.listening_level && (
                    <div>
                      <p className="text-sm text-muted-foreground mb-1">聞く</p>
                      <p className="text-foreground font-medium">{candidate.listening_level}</p>
                    </div>
                  )}

                  {candidate.speaking_level && (
                    <div>
                      <p className="text-sm text-muted-foreground mb-1">話す</p>
                      <p className="text-foreground font-medium">{candidate.speaking_level}</p>
                    </div>
                  )}

                  {candidate.reading_level && (
                    <div>
                      <p className="text-sm text-muted-foreground mb-1">読む</p>
                      <p className="text-foreground font-medium">{candidate.reading_level}</p>
                    </div>
                  )}

                  {candidate.writing_level && (
                    <div>
                      <p className="text-sm text-muted-foreground mb-1">書く</p>
                      <p className="text-foreground font-medium">{candidate.writing_level}</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Work Experience */}
            {hasExperience && (
              <div className="bg-card rounded-2xl shadow-sm border border-input p-6">
                <div className="flex items-center gap-2 mb-4">
                  <div className="p-2 bg-gradient-to-r from-orange-500 to-red-500 rounded-lg">
                    <BriefcaseIcon className="h-5 w-5 text-white" />
                  </div>
                  <h3 className="text-lg font-semibold text-foreground">経験作業内容</h3>
                </div>

                <div className="flex flex-wrap gap-2">
                  {experienceFields.map(field => (
                    candidate[field.key as keyof Candidate] && (
                      <span key={field.key} className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300">
                        <CheckCircleIcon className="h-4 w-4 mr-1" />
                        {field.label}
                      </span>
                    )
                  ))}
                </div>

                {candidate.exp_other && (
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <p className="text-sm text-gray-500 mb-1">その他</p>
                    <p className="text-gray-900">{candidate.exp_other}</p>
                  </div>
                )}
              </div>
            )}

            {/* Emergency Contact */}
            {(candidate.emergency_contact_name || candidate.emergency_contact_phone) && (
              <div className="bg-card rounded-2xl shadow-sm border border-input p-6">
                <div className="flex items-center gap-2 mb-4">
                  <div className="p-2 bg-gradient-to-r from-red-500 to-pink-500 rounded-lg">
                    <ExclamationTriangleIcon className="h-5 w-5 text-white" />
                  </div>
                  <h3 className="text-lg font-semibold text-foreground">緊急連絡先</h3>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {candidate.emergency_contact_name && (
                    <div>
                      <p className="text-sm text-muted-foreground mb-1">氏名</p>
                      <p className="text-foreground font-medium">{candidate.emergency_contact_name}</p>
                    </div>
                  )}

                  {candidate.emergency_contact_relation && (
                    <div>
                      <p className="text-sm text-muted-foreground mb-1">続柄</p>
                      <p className="text-foreground">{candidate.emergency_contact_relation}</p>
                    </div>
                  )}

                  {candidate.emergency_contact_phone && (
                    <div>
                      <p className="text-sm text-muted-foreground mb-1">電話番号</p>
                      <p className="text-foreground">{candidate.emergency_contact_phone}</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* System Info */}
            <div className="bg-muted rounded-2xl border border-input p-6">
              <h3 className="text-sm font-semibold text-foreground mb-3">システム情報</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                {candidate.created_at && (
                  <div>
                    <p className="text-muted-foreground">登録日時</p>
                    <p className="text-foreground">{new Date(candidate.created_at).toLocaleString('ja-JP')}</p>
                  </div>
                )}

                {candidate.updated_at && (
                  <div>
                    <p className="text-muted-foreground">更新日時</p>
                    <p className="text-foreground">{new Date(candidate.updated_at).toLocaleString('ja-JP')}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
