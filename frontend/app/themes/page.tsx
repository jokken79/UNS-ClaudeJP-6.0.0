'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function ThemesRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/dashboard/themes');
  }, [router]);

  return null;
}
