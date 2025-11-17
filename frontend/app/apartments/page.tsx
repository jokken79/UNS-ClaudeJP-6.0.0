'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function ApartmentsRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/dashboard/apartments');
  }, [router]);

  return null;
}
