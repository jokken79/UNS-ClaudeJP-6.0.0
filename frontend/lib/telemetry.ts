'use client';

import { useEffect } from 'react';

let telemetryStarted = false;

/**
 * Telemetry hook for OpenTelemetry integration
 *
 * Currently disabled - install @opentelemetry packages to enable.
 * See documentation for setup instructions.
 */
export const useTelemetry = () => {
  useEffect(() => {
    if (telemetryStarted || typeof window === 'undefined') {
      return;
    }

    // OpenTelemetry initialization disabled
    // Install required packages and configure to enable telemetry

    telemetryStarted = true;

    return () => {
      // Cleanup if needed
      telemetryStarted = false;
    };
  }, []);
};
