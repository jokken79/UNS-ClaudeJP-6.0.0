'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function EmployeesRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/dashboard/employees');
  }, [router]);

  return null;
}
