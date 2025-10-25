import { useEffect } from 'react';
import { useToast } from './ToastContainer';
import { setToastInstance } from '@/utils/errorHandler';

/**
 * Component to initialize the global toast instance
 * This connects the toast system to the error handler
 */
export default function ToastInitializer() {
  const toast = useToast();

  useEffect(() => {
    setToastInstance(toast);
    console.log('[Toast] Sistema de notificações inicializado');

    return () => {
      setToastInstance(null);
    };
  }, [toast]);

  return null;
}
