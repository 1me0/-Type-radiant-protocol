// frontend/Index.tsx
// Entry point for the Radiant Protocol frontend.
// Initialises the React application with StrictMode and error logging.

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

/**
 * Handles recoverable errors during rendering (e.g., suspense fallbacks, render errors).
 * In production, you can send these to a monitoring service like Sentry.
 */
const onRecoverableError = (error: Error, errorInfo: React.ErrorInfo) => {
  console.error('[Radiant] Recoverable error:', error, errorInfo);
  // Optional: send to external monitoring
  // if (process.env.NODE_ENV === 'production') {
  //   Sentry.captureException(error, { extra: errorInfo });
  // }
};

// Create root with custom error handler
const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement,
  { onRecoverableError }
);

// Render the app
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
