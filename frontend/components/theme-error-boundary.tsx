'use client';

import { ReactNode, Component, ErrorInfo } from 'react';
import { AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error Boundary for Theme System Components
 *
 * Catches and handles errors in theme-related components gracefully.
 * Shows a user-friendly error message with recovery options.
 *
 * Usage:
 * ```tsx
 * <ThemeErrorBoundary>
 *   <ThemeSwitcher />
 * </ThemeErrorBoundary>
 * ```
 */
export class ThemeErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error details for debugging
    console.error('Theme Error Boundary caught an error:', error);
    console.error('Error Info:', errorInfo);
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
    });
  };

  handleReload = () => {
    // Hard refresh to reset application state
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center min-h-screen p-4 bg-background">
          <Card className="w-full max-w-md border-destructive/20">
            <CardHeader>
              <div className="flex items-center gap-3">
                <AlertCircle className="h-6 w-6 text-destructive" />
                <div>
                  <CardTitle>Theme System Error</CardTitle>
                  <CardDescription>
                    Something went wrong with the theme system
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Error Details (Development Only) */}
              {process.env.NODE_ENV === 'development' && this.state.error && (
                <div className="space-y-2">
                  <div className="text-sm font-mono bg-muted p-3 rounded overflow-auto max-h-40 text-destructive">
                    <div className="font-bold mb-1">Error Message:</div>
                    {this.state.error.message}
                    {this.state.error.stack && (
                      <>
                        <div className="font-bold mt-2 mb-1">Stack:</div>
                        <div className="text-xs">{this.state.error.stack}</div>
                      </>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    This error information is only visible in development mode.
                  </p>
                </div>
              )}

              {/* User-Friendly Message */}
              {process.env.NODE_ENV === 'production' && (
                <div className="space-y-2 text-sm text-muted-foreground">
                  <p>
                    We encountered an issue with the theme system. Try one of the following:
                  </p>
                  <ul className="list-disc list-inside space-y-1">
                    <li>Clear your browser cache and reload</li>
                    <li>Check if localStorage is available and has space</li>
                    <li>Try a different browser</li>
                    <li>Disable browser extensions that might interfere</li>
                  </ul>
                </div>
              )}

              {/* Recovery Actions */}
              <div className="flex gap-2 pt-2">
                <Button
                  variant="outline"
                  onClick={this.handleReset}
                  className="flex-1"
                >
                  Try Again
                </Button>
                <Button
                  variant="default"
                  onClick={this.handleReload}
                  className="flex-1"
                >
                  Reload Page
                </Button>
              </div>

              {/* Support Information */}
              <div className="text-xs text-muted-foreground border-t pt-3">
                <p>
                  If the problem persists, please{' '}
                  <a
                    href="https://github.com/jokken79/UNS-ClaudeJP-6.0.0/issues"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline"
                  >
                    report the issue on GitHub
                  </a>
                  .
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}
