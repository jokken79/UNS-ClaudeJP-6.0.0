'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Loader2 } from 'lucide-react';

export default function SettingsPage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to appearance settings by default
    router.replace('/dashboard/settings/appearance');
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
        <p className="text-muted-foreground">Cargando configuración...</p>
      </div>
    </div>
  );
}
