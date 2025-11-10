'use client';

import { useMemo, useState } from 'react';
import Image from 'next/image';
import { toast } from 'react-hot-toast';
import {
  ArrowUpTrayIcon,
  CheckCircleIcon,
  CloudArrowUpIcon,
  DocumentMagnifyingGlassIcon,
  PhotoIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

/**
 * AzureOCRUploader Component
 *
 * This component handles OCR processing for multiple document types (Zairyu Card, License).
 *
 * DATA FLOW:
 * 1. User uploads document(s) → Azure OCR API processes
 * 2. Raw OCR results preserved with original field names (e.g., name_kanji, license_number)
 * 3. Multiple document results combined (Zairyu Card has priority)
 * 4. Combined RAW data sent to onResult callback
 * 5. Parent component (e.g., handleAzureOcrComplete) maps to form fields
 *
 * IMPORTANT: This component does NOT map field names. It sends raw OCR data.
 */

interface AzureOCRUploaderProps {
  onResult: (data: Record<string, unknown>) => void;
  defaultDocumentType?: 'zairyu_card' | 'license' | 'rirekisho';
}

type DocumentType = 'zairyu_card' | 'license';

interface AzureOCRResponse {
  success: boolean;
  data?: Record<string, unknown>;
  message?: string;
}

interface UploadedDocument {
  file: File | null;
  previewUrl: string | null;
  documentType: DocumentType;
  isProcessing: boolean;
  progress: number;
  result: Record<string, unknown> | null;
}

const MAX_FILE_SIZE = 8 * 1024 * 1024; // 8 MB safety limit for high-resolution scans

const SUPPORTED_TYPES = ['image/jpeg', 'image/png', 'image/heic', 'image/heif'];

function isSupportedType(file: File) {
  if (SUPPORTED_TYPES.includes(file.type)) return true;
  // Some browsers report HEIC/HEIF as application/octet-stream
  if (file.name.toLowerCase().endsWith('.heic') || file.name.toLowerCase().endsWith('.heif')) {
    return true;
  }
  return false;
}

// Combine raw OCR results from multiple documents
// Priority: Zairyu Card fields first, then License fields supplement missing data
function combineOCRResults(
  zairyuResult: Record<string, unknown> | null,
  licenseResult: Record<string, unknown> | null
): Record<string, unknown> {
  const combined: Record<string, unknown> = {};

  // Copy all fields from Zairyu Card first (highest priority)
  if (zairyuResult) {
    Object.assign(combined, zairyuResult);
    // Mark that data came from Zairyu Card
    combined._sourceDocuments = ['zairyu_card'];
  }

  // Add fields from License (only if not already present, except for license-specific fields)
  if (licenseResult) {
    // License-specific fields always added (these are unique to license)
    if (licenseResult.license_number) combined.license_number = licenseResult.license_number;
    if (licenseResult.menkyo_number) combined.menkyo_number = licenseResult.menkyo_number;
    if (licenseResult.license_expiry) combined.license_expiry = licenseResult.license_expiry;
    if (licenseResult.license_expire_date) combined.license_expire_date = licenseResult.license_expire_date;
    if (licenseResult.license_type) combined.license_type = licenseResult.license_type;

    // Common fields that may appear in both documents (only add if not present from Zairyu)
    const commonFields = [
      'name_kanji', 'full_name_kanji', 'name_roman',
      'name_kana', 'full_name_kana', 'name_katakana',
      'birthday', 'date_of_birth',
      'address', 'current_address', 'registered_address',
      'postal_code', 'zip_code',
      'gender',
      'photo', 'photo_url', 'face_photo'
    ];

    for (const field of commonFields) {
      if (licenseResult[field] && !combined[field]) {
        combined[field] = licenseResult[field];
      }
    }

    // Update the list of source documents
    if (combined._sourceDocuments) {
      (combined._sourceDocuments as string[]).push('license');
    } else {
      combined._sourceDocuments = ['license'];
    }
  }

  return combined;
}

export function AzureOCRUploader({ onResult }: AzureOCRUploaderProps) {
  const [zairyuDoc, setZairyuDoc] = useState<UploadedDocument>({
    file: null,
    previewUrl: null,
    documentType: 'zairyu_card',
    isProcessing: false,
    progress: 0,
    result: null,
  });

  const [licenseDoc, setLicenseDoc] = useState<UploadedDocument>({
    file: null,
    previewUrl: null,
    documentType: 'license',
    isProcessing: false,
    progress: 0,
    result: null,
  });

  const resetDocument = (docType: DocumentType) => {
    if (docType === 'zairyu_card') {
      setZairyuDoc({
        file: null,
        previewUrl: null,
        documentType: 'zairyu_card',
        isProcessing: false,
        progress: 0,
        result: null,
      });
    } else {
      setLicenseDoc({
        file: null,
        previewUrl: null,
        documentType: 'license',
        isProcessing: false,
        progress: 0,
        result: null,
      });
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>, docType: DocumentType) => {
    const selected = event.target.files?.[0];
    if (!selected) return;

    if (!isSupportedType(selected)) {
      toast.error('対応していないファイル形式です。JPG / PNG / HEIC 画像を使用してください。');
      return;
    }

    if (selected.size > MAX_FILE_SIZE) {
      toast.error('ファイルサイズが大きすぎます。8MB 以下の画像を選択してください。');
      return;
    }

    const updateDoc = (previewUrl: string | null) => {
      if (docType === 'zairyu_card') {
        setZairyuDoc((prev) => ({
          ...prev,
          file: selected,
          previewUrl,
        }));
      } else {
        setLicenseDoc((prev) => ({
          ...prev,
          file: selected,
          previewUrl,
        }));
      }
    };

    if (selected.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = () => updateDoc(reader.result as string);
      reader.readAsDataURL(selected);
    } else {
      updateDoc(null);
    }
  };

  const uploadToAzure = async (docType: DocumentType) => {
    const doc = docType === 'zairyu_card' ? zairyuDoc : licenseDoc;
    const setDoc = docType === 'zairyu_card' ? setZairyuDoc : setLicenseDoc;

    if (!doc.file) {
      toast.error('先に画像ファイルを選択してください。');
      return;
    }

    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    if (!token) {
      toast.error('認証トークンが見つかりません。再ログインしてください。');
      return;
    }

    setDoc((prev) => ({ ...prev, isProcessing: true, progress: 10 }));

    const formData = new FormData();
    formData.append('file', doc.file);
    formData.append('document_type', docType);

    try {
      const response = await fetch(`${API_BASE_URL}/azure-ocr/process`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorPayload = await response.json().catch(() => ({}));
        throw new Error(errorPayload.detail || 'Azure OCR の処理に失敗しました。');
      }

      setDoc((prev) => ({ ...prev, progress: 85 }));
      const payload = (await response.json()) as AzureOCRResponse;

      if (!payload?.success || !payload?.data) {
        throw new Error('OCR の結果が空です。もう一度お試しください。');
      }

      setDoc((prev) => ({ ...prev, progress: 100, result: payload.data || null }));
      toast.success(`${docType === 'zairyu_card' ? '在留カード' : '免許証'}の解析が完了しました。`);

      // Combine raw results and call onResult
      // Note: We send RAW OCR data with original field names (e.g., name_kanji, license_number)
      // The receiving component (handleAzureOcrComplete) will map to form fields
      const currentZairyuResult = docType === 'zairyu_card' ? payload.data : zairyuDoc.result;
      const currentLicenseResult = docType === 'license' ? payload.data : licenseDoc.result;

      const combinedData = combineOCRResults(
        currentZairyuResult || null,
        currentLicenseResult || null
      );

      onResult(combinedData);
    } catch (error: unknown) {
      console.error('Azure OCR upload error', error);
      const message = error instanceof Error ? error.message : 'Azure OCR の呼び出しに失敗しました。';
      toast.error(message);
    } finally {
      setDoc((prev) => ({ ...prev, isProcessing: false }));
      setTimeout(() => {
        setDoc((prev) => ({ ...prev, progress: 0 }));
      }, 1200);
    }
  };

  const renderDocumentSection = (
    doc: UploadedDocument,
    title: string,
    description: string,
    inputId: string
  ) => (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center gap-3 mb-4">
        <DocumentMagnifyingGlassIcon className="h-6 w-6 text-sky-600" />
        <div>
          <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
          <p className="text-sm text-slate-500">{description}</p>
        </div>
      </div>

      <div className="space-y-4">
        <div className="flex flex-col gap-3 rounded-lg border border-slate-200 p-4">
          {!doc.file ? (
            <label className="flex h-40 cursor-pointer flex-col items-center justify-center gap-3 rounded-md border-2 border-dashed border-slate-300 bg-slate-50 text-center transition hover:border-sky-400 hover:bg-sky-50">
              <CloudArrowUpIcon className="h-10 w-10 text-sky-500" />
              <div className="text-sm font-medium text-slate-600">
                ファイルをドラッグ＆ドロップ、またはクリックして選択
              </div>
              <div className="text-xs text-slate-400">JPG / PNG / HEIC, 最大 8MB</div>
              <input
                id={inputId}
                type="file"
                accept="image/*,.heic,.heif"
                className="hidden"
                onChange={(e) => handleFileChange(e, doc.documentType)}
                disabled={doc.isProcessing}
              />
            </label>
          ) : (
            <div className="relative overflow-hidden rounded-md border border-slate-200">
              <button
                type="button"
                className="absolute right-2 top-2 rounded-full bg-white/80 p-1 text-slate-500 shadow hover:text-rose-500 z-10"
                onClick={() => resetDocument(doc.documentType)}
                disabled={doc.isProcessing}
                title="選択をクリア"
              >
                <XMarkIcon className="h-5 w-5" />
              </button>
              {doc.previewUrl ? (
                <Image
                  src={doc.previewUrl}
                  alt="ドキュメントプレビュー"
                  width={600}
                  height={384}
                  className="h-48 w-full object-contain bg-white"
                  unoptimized
                />
              ) : (
                <div className="flex h-48 items-center justify-center bg-slate-100 text-sm text-slate-500">
                  <PhotoIcon className="mr-2 h-6 w-6" /> プレビューなし
                </div>
              )}
              <div className="border-t border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-500">
                {doc.file.name}・{(doc.file.size / 1024 / 1024).toFixed(2)} MB
              </div>
            </div>
          )}

          {doc.progress > 0 && (
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs text-slate-500">
                <span>解析進行状況</span>
                <span>{doc.progress}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-200">
                <div
                  className="h-full rounded-full bg-sky-500 transition-all"
                  style={{ width: `${Math.min(doc.progress, 100)}%` }}
                ></div>
              </div>
            </div>
          )}

          <button
            type="button"
            onClick={() => uploadToAzure(doc.documentType)}
            disabled={!doc.file || doc.isProcessing}
            className={`inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-semibold text-white shadow-sm transition ${
              !doc.file || doc.isProcessing
                ? 'bg-sky-300 cursor-not-allowed'
                : 'bg-sky-600 hover:bg-sky-700 focus:outline-none focus:ring-2 focus:ring-sky-300'
            }`}
          >
            <ArrowUpTrayIcon className="h-4 w-4" />
            {doc.isProcessing ? 'OCR 解析中…' : 'OCR実行'}
          </button>

          {doc.result && (
            <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-xs">
              <p className="flex items-center gap-2 font-medium text-emerald-700">
                <CheckCircleIcon className="h-4 w-4" />
                解析完了
              </p>
              <p className="mt-1 text-emerald-600">
                データが正常に抽出されました。フォームに反映されています。
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-gradient-to-r from-sky-50 to-blue-50 p-6 shadow-sm">
        <div className="flex items-start gap-3">
          <DocumentMagnifyingGlassIcon className="h-6 w-6 text-sky-600 flex-shrink-0 mt-1" />
          <div>
            <h2 className="text-xl font-bold text-slate-900 mb-2">
              複数ドキュメント OCR アップロード
            </h2>
            <p className="text-sm text-slate-600 mb-3">
              在留カードと免許証の両方をアップロードできます。各ドキュメントを個別に処理し、
              抽出されたデータは自動的に結合されてフォームに反映されます。
            </p>
            <div className="rounded-md border border-sky-200 bg-white/50 p-3 text-xs text-slate-600">
              <p className="flex items-center gap-2 font-medium text-sky-700 mb-2">
                <CheckCircleIcon className="h-4 w-4" />
                推奨スキャンのポイント
              </p>
              <ul className="list-disc space-y-1 pl-5">
                <li>書類の四隅が収まるように撮影してください。</li>
                <li>影や反射を避け、文字が鮮明に読める画像を使用してください。</li>
                <li>在留カードのデータが優先され、免許証のデータで補完されます。</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {renderDocumentSection(
          zairyuDoc,
          '在留カード',
          '在留資格、在留期限、カード番号などを抽出します',
          'zairyu-file-input'
        )}
        {renderDocumentSection(
          licenseDoc,
          '運転免許証',
          '免許証番号、有効期限などを抽出します',
          'license-file-input'
        )}
      </div>

      <div className="rounded-md border border-slate-200 bg-slate-50 p-4 text-xs text-slate-600">
        <p className="font-medium text-slate-700 mb-2">サンプル画像でテストするには:</p>
        <ul className="list-disc space-y-1 pl-5">
          <li>
            在留カード: <code className="rounded bg-slate-800/10 px-1">backend/zairyu.jpg</code> を使用
          </li>
          <li>
            免許証: <code className="rounded bg-slate-800/10 px-1">backend/menkyo.png</code> を使用
          </li>
          <li>両方のドキュメントを処理すると、データが自動的に結合されます。</li>
        </ul>
      </div>
    </div>
  );
}

export default AzureOCRUploader;
