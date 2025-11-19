'use client';

import { useEffect } from 'react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Error in root page:', error);
  }, [error]);

  return (
    <div style={{ padding: '20px', fontFamily: 'system-ui' }}>
      <h1>Application Error</h1>
      <h2>Something went wrong</h2>
      <pre style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word', backgroundColor: '#f5f5f5', padding: '10px', borderRadius: '4px' }}>
        {error.message}
      </pre>
      <button
        onClick={reset}
        style={{
          padding: '10px 20px',
          backgroundColor: '#007bff',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '14px'
        }}
      >
        Try again
      </button>
    </div>
  );
}
