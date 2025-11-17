'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function TimerCardsRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/dashboard/timercards');
  }, [router]);

  return null;
}
