// Debug utility to log API configuration
export function logAPIConfig() {
  const config = {
    VITE_API_URL: import.meta.env.VITE_API_URL,
    API_BASE: import.meta.env.VITE_API_URL ? 
      (import.meta.env.VITE_API_URL.replace(/\/$/, '') + (import.meta.env.VITE_API_URL.includes('/api') ? '' : '/api')) :
      'http://localhost:8001/api',
    mode: import.meta.env.MODE,
    dev: import.meta.env.DEV,
    prod: import.meta.env.PROD,
  };
  console.log('🔍 API Configuration:', config);
  return config;
}
