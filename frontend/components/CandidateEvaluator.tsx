'use client';

import { useState } from 'react';
import { ThumbsUp, ThumbsDown, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

interface CandidateEvaluatorProps {
  candidateId: number;
  candidateName: string;
  onSuccess?: () => void;
}

export function CandidateEvaluator({
  candidateId,
  candidateName,
  onSuccess
}: CandidateEvaluatorProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [notes, setNotes] = useState('');
  const [selectedAction, setSelectedAction] = useState<'approve' | 'reject' | null>(null);

  const handleEvaluation = async (approved: boolean) => {
    try {
      setIsLoading(true);

      await fetch(`/candidates/${candidateId}/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          approved,
          notes: notes.trim() || null
        })
      });

      const action = approved ? '承認しました' : 'ペンディング状態に変更しました';
      alert(`${candidateName}を${action}`);

      setNotes('');
      setSelectedAction(null);

      if (onSuccess) {
        onSuccess();
      }
    } catch (error) {
      console.error('Evaluation error:', error);
      alert('評価の保存に失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-4 border rounded-lg p-4 bg-card">
      <h3 className="font-semibold text-sm">クイック評価 (Quick Evaluation)</h3>

      {/* Notes textarea */}
      <Textarea
        placeholder="評価コメント（オプション）... (Optional evaluation notes)"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        className="min-h-24 text-sm"
        disabled={isLoading}
      />

      {/* Action buttons */}
      <div className="flex gap-2">
        <Button
          variant={selectedAction === 'approve' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setSelectedAction(selectedAction === 'approve' ? null : 'approve')}
          disabled={isLoading}
          className="flex-1 gap-2"
        >
          <ThumbsUp className="w-4 h-4" />
          承認 (Approve)
        </Button>

        <Button
          variant={selectedAction === 'reject' ? 'destructive' : 'outline'}
          size="sm"
          onClick={() => setSelectedAction(selectedAction === 'reject' ? null : 'reject')}
          disabled={isLoading}
          className="flex-1 gap-2"
        >
          <ThumbsDown className="w-4 h-4" />
          ペンディング (Pending)
        </Button>
      </div>

      {/* Confirm button */}
      {selectedAction && (
        <Button
          className="w-full gap-2"
          onClick={() => handleEvaluation(selectedAction === 'approve')}
          disabled={isLoading}
        >
          {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
          {isLoading ? '保存中...' : 'Save Evaluation'}
        </Button>
      )}
    </div>
  );
}
