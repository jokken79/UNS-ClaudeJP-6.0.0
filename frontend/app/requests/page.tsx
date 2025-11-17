'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function RequestsRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/dashboard/requests');
  }, [router]);

  return null;
}
