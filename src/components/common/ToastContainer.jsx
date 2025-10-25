import { createContext, useContext, useState, useCallback, useRef } from 'react';
import Toast from './Toast';

const ToastContext = createContext(null);

const MAX_TOASTS = 5; // Limit simultaneous toasts
const DEBOUNCE_TIME = 300; // Prevent duplicate toasts within 300ms

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const recentToastsRef = useRef(new Map()); // Track recent toasts for debouncing

  const addToast = useCallback((type, message, duration = 5000) => {
    // Create a unique key for this toast
    const toastKey = `${type}-${message}`;
    const now = Date.now();

    // Check if this exact toast was recently shown (debounce)
    const lastShown = recentToastsRef.current.get(toastKey);
    if (lastShown && now - lastShown < DEBOUNCE_TIME) {
      console.log('[Toast] Debounced duplicate notification');
      return;
    }

    // Update recent toasts map
    recentToastsRef.current.set(toastKey, now);

    // Clean up old entries from the map
    setTimeout(() => {
      recentToastsRef.current.delete(toastKey);
    }, DEBOUNCE_TIME);

    const id = Date.now() + Math.random();

    setToasts((prev) => {
      // Limit the number of toasts
      const newToasts = [...prev, { id, type, message, duration }];
      if (newToasts.length > MAX_TOASTS) {
        // Remove oldest toast
        return newToasts.slice(1);
      }
      return newToasts;
    });
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const toast = {
    success: (message, duration) => addToast('success', message, duration),
    error: (message, duration) => addToast('error', message, duration),
    warning: (message, duration) => addToast('warning', message, duration),
    info: (message, duration) => addToast('info', message, duration),
  };

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 max-w-md pointer-events-none">
        {toasts.map((toast) => (
          <Toast
            key={toast.id}
            type={toast.type}
            message={toast.message}
            duration={toast.duration}
            onClose={() => removeToast(toast.id)}
          />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
}
