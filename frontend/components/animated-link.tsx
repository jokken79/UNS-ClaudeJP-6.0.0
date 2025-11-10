/**
 * Animated Link Component
 *
 * Enhanced Next.js Link with smooth transitions, prefetching,
 * and loading indicators.
 */

'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { type ComponentProps, type ReactNode, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { type TransitionVariant } from '@/lib/route-transitions';
import { withViewTransition } from '@/lib/view-transitions';

export interface AnimatedLinkProps extends Omit<ComponentProps<typeof Link>, 'href'> {
  href: string;
  children: ReactNode;
  variant?: TransitionVariant;
  showProgress?: boolean;
  prefetchOnHover?: boolean;
  className?: string;
  activeClassName?: string;
}

export function AnimatedLink({
  href,
  children,
  variant = 'fade',
  showProgress = false,
  prefetchOnHover = true,
  className,
  activeClassName,
  onClick,
  ...props
}: AnimatedLinkProps) {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [isPrefetched, setIsPrefetched] = useState(false);

  const handleClick = useCallback(
    async (e: React.MouseEvent<HTMLAnchorElement>) => {
      // Call original onClick if provided
      if (onClick) {
        onClick(e);
      }

      // If default prevented, don't navigate
      if (e.defaultPrevented) {
        return;
      }

      // Handle external links normally
      if (href.startsWith('http') || href.startsWith('mailto:')) {
        return;
      }

      // For internal links, use View Transitions API if available
      e.preventDefault();
      setIsLoading(true);

      try {
        await withViewTransition(() => {
          router.push(href);
        });
      } catch (error) {
        console.error('Navigation failed:', error);
      } finally {
        setIsLoading(false);
      }
    },
    [href, onClick, router]
  );

  const handleMouseEnter = useCallback(() => {
    if (prefetchOnHover && !isPrefetched && !href.startsWith('http')) {
      // Prefetch the route
      router.prefetch(href);
      setIsPrefetched(true);
    }
  }, [prefetchOnHover, isPrefetched, href, router]);

  return (
    <Link
      href={href}
      onClick={handleClick}
      onMouseEnter={handleMouseEnter}
      className={cn(
        'relative inline-flex items-center transition-colors',
        className
      )}
      {...props}
    >
      {children}

      {/* Loading Indicator */}
      {showProgress && isLoading && (
        <motion.span
          className="absolute inset-0 bg-primary/10 rounded"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        />
      )}
    </Link>
  );
}

/**
 * Animated button-style link with ripple effect
 */
export function AnimatedButtonLink({
  href,
  children,
  className,
  ...props
}: AnimatedLinkProps) {
  const [ripples, setRipples] = useState<Array<{ x: number; y: number; id: number }>>([]);

  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const newRipple = {
      x,
      y,
      id: Date.now(),
    };

    setRipples((prev) => [...prev, newRipple]);

    // Remove ripple after animation
    setTimeout(() => {
      setRipples((prev) => prev.filter((r) => r.id !== newRipple.id));
    }, 600);

    // Call original onClick if provided
    if (props.onClick) {
      props.onClick(e);
    }
  };

  return (
    <AnimatedLink
      href={href}
      className={cn(
        'relative overflow-hidden',
        className
      )}
      onClick={handleClick}
      {...props}
    >
      {children}

      {/* Ripple Effects */}
      {ripples.map((ripple) => (
        <motion.span
          key={ripple.id}
          className="absolute rounded-full bg-white/30 pointer-events-none"
          style={{
            left: ripple.x,
            top: ripple.y,
          }}
          initial={{
            width: 0,
            height: 0,
            x: 0,
            y: 0,
            opacity: 1,
          }}
          animate={{
            width: 500,
            height: 500,
            x: -250,
            y: -250,
            opacity: 0,
          }}
          transition={{
            duration: 0.6,
            ease: 'easeOut',
          }}
        />
      ))}
    </AnimatedLink>
  );
}

/**
 * Navigation link with active state indicator
 */
export function NavLink({
  href,
  children,
  activeClassName = 'text-primary font-semibold',
  className,
  ...props
}: AnimatedLinkProps & { isActive?: boolean }) {
  return (
    <AnimatedLink
      href={href}
      className={cn(
        'group relative px-3 py-2 rounded-md transition-all',
        'hover:bg-accent hover:text-accent-foreground',
        className
      )}
      {...props}
    >
      {children}

      {/* Active Indicator */}
      <motion.span
        className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary"
        initial={{ scaleX: 0 }}
        whileHover={{ scaleX: 1 }}
        transition={{ duration: 0.2 }}
      />
    </AnimatedLink>
  );
}
