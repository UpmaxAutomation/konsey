/**
 * Frontend monitoring — Sentry initialization and Web Vitals reporting.
 * @module utils/monitoring
 */

/**
 * Initialize Sentry for frontend error and performance monitoring.
 * Only activates if VITE_SENTRY_DSN environment variable is set.
 */
export async function initSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  if (!dsn) return;

  try {
    const Sentry = await import('@sentry/react');
    Sentry.init({
      dsn,
      environment: import.meta.env.MODE || 'development',
      tracesSampleRate: import.meta.env.MODE === 'production' ? 0.2 : 1.0,
      replaysSessionSampleRate: 0,
      replaysOnErrorSampleRate: 1.0,
      integrations: [
        Sentry.browserTracingIntegration(),
        Sentry.replayIntegration(),
      ],
    });
  } catch (err) {
    console.warn('Sentry initialization skipped:', err.message);
  }
}

/**
 * Report Core Web Vitals (CLS, FID, LCP, FCP, TTFB).
 * Sends metrics to Sentry custom metrics or logs to console.
 */
export async function reportWebVitals() {
  try {
    const { onCLS, onFID, onLCP, onFCP, onTTFB } = await import('web-vitals');
    const handleMetric = (metric) => {
      // Log to console in development
      if (import.meta.env.DEV) {
        console.log(`[Web Vital] ${metric.name}: ${metric.value.toFixed(2)}`);
      }
      // Send to Sentry if available
      try {
        const Sentry = window.__SENTRY__;
        if (Sentry?.captureMessage) {
          Sentry.captureMessage(`Web Vital: ${metric.name}`, {
            level: 'info',
            extra: { value: metric.value, rating: metric.rating },
          });
        }
      } catch {
        // Sentry not available, metric already logged
      }
    };

    onCLS(handleMetric);
    onFID(handleMetric);
    onLCP(handleMetric);
    onFCP(handleMetric);
    onTTFB(handleMetric);
  } catch (err) {
    // web-vitals not installed, skip silently
  }
}

/**
 * Track a custom interaction timing.
 * @param {string} name - Interaction name
 * @param {number} duration - Duration in milliseconds
 */
export function trackInteraction(name, duration) {
  if (import.meta.env.DEV) {
    console.log(`[Perf] ${name}: ${duration.toFixed(1)}ms`);
  }
}
