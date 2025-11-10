'use client';

import { useAuthStore } from '@/stores/auth-store';
import { useSettingsStore } from '@/stores/settings-store';
import { UnderConstruction } from './under-construction';
import { useEffect } from 'react';

interface VisibilityGuardProps {
  children: React.ReactNode;
}

export function VisibilityGuard({ children }: VisibilityGuardProps) {
  const { user } = useAuthStore();
  const { visibilityEnabled, fetchVisibilityToggle } = useSettingsStore();

  useEffect(() => {
    // Only fetch if user is authenticated
    if (user) {
      fetchVisibilityToggle();
    }
  }, [user]); // Only depend on user, not the function itself

  // Check if user should see construction page
  // Only ADMIN and KANRINSHA are affected by the toggle
  const isAffectedRole = user?.role === 'ADMIN' || user?.role === 'KANRINSHA';
  const shouldShowConstruction = isAffectedRole && !visibilityEnabled;

  if (shouldShowConstruction) {
    return <UnderConstruction />;
  }

  return <>{children}</>;
}
