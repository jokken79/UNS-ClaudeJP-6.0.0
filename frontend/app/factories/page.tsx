'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function FactoriesRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/dashboard/factories');
  }, [router]);

  return null;
}
