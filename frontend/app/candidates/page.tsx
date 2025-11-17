'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function CandidatesRedirect() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to dashboard/candidates
    router.replace('/dashboard/candidates');
  }, [router]);

  return null;
}
