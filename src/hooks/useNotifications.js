import { useState, useEffect, useCallback, useRef } from 'react';
import { getNotifications, markAsRead, markAllAsRead } from '@/services/api/notifications';

/**
 * Hook para gerenciar notificações do sistema
 *
 * Features:
 * - Busca notificações do backend (baseado em logs)
 * - Polling automático a cada 30 segundos
 * - Marca como lida/não lida
 * - Filtra por conta
 * - Contagem de não lidas
 */
export function useNotifications(options = {}) {
  const {
    pollingInterval = 30000, // 30 segundos
    limit = 20,
    account = null,
    autoStart = true,
  } = options;

  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const pollingRef = useRef(null);
  const mountedRef = useRef(true);
  const isFirstLoadRef = useRef(true);

  /**
   * Busca notificações do servidor
   */
  const fetchNotifications = useCallback(async () => {
    // Só mostra loading na primeira carga
    const shouldShowLoading = isFirstLoadRef.current;

    try {
      if (shouldShowLoading) {
        console.log('[useNotifications] Ativando loading...');
        setLoading(true);
      }
      setError(null);

      console.log('[useNotifications] Iniciando busca de notificações...');
      const data = await getNotifications({ limit, account });
      console.log('[useNotifications] Promise resolvida! Dados recebidos:', data);

      console.log('[useNotifications] Atualizando estado com', data?.length || 0, 'notificações');
      setNotifications(data || []);
      isFirstLoadRef.current = false;
    } catch (err) {
      console.error('[useNotifications] Erro capturado:', err);
      setError(err.message || 'Erro ao buscar notificações');
      setNotifications([]); // Define array vazio em caso de erro
    } finally {
      if (shouldShowLoading) {
        console.log('[useNotifications] Finalizando loading...');
        setLoading(false);
      }
    }
  }, [limit, account]);

  /**
   * Marca notificação como lida
   */
  const markRead = useCallback(async (notificationId) => {
    try {
      await markAsRead(notificationId);

      // Atualiza estado local
      setNotifications(prev =>
        prev.map(n =>
          n.id === notificationId ? { ...n, read: true } : n
        )
      );
    } catch (err) {
      console.error('[useNotifications] Erro ao marcar como lida:', err);
    }
  }, []);

  /**
   * Marca todas como lidas
   */
  const markAllRead = useCallback(async () => {
    try {
      await markAllAsRead(notifications);

      // Atualiza estado local
      setNotifications(prev =>
        prev.map(n => ({ ...n, read: true }))
      );
    } catch (err) {
      console.error('[useNotifications] Erro ao marcar todas como lidas:', err);
    }
  }, [notifications]);

  /**
   * Atualiza manualmente
   */
  const refresh = useCallback(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  /**
   * Inicia polling
   */
  const startPolling = useCallback(() => {
    if (pollingRef.current) return; // Já está rodando

    // Busca imediatamente
    fetchNotifications();

    // Configura polling
    pollingRef.current = setInterval(() => {
      fetchNotifications();
    }, pollingInterval);

    console.log(`[useNotifications] Polling iniciado (intervalo: ${pollingInterval}ms)`);
  }, [fetchNotifications, pollingInterval]);

  /**
   * Para polling
   */
  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
      console.log('[useNotifications] Polling parado');
    }
  }, []);

  /**
   * Lifecycle: inicia/para polling
   */
  useEffect(() => {
    if (autoStart) {
      // Busca imediatamente
      fetchNotifications();

      // Configura polling
      pollingRef.current = setInterval(() => {
        fetchNotifications();
      }, pollingInterval);

      console.log(`[useNotifications] Polling iniciado (intervalo: ${pollingInterval}ms)`);
    }

    return () => {
      // Apenas limpa o polling, NÃO marca como desmontado aqui
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
        console.log('[useNotifications] Polling parado');
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoStart, pollingInterval]);

  /**
   * Cleanup final: marca como desmontado apenas quando o componente for destruído
   */
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      console.log('[useNotifications] Componente desmontado definitivamente');
    };
  }, []);

  /**
   * Contadores
   */
  const unreadCount = notifications.filter(n => !n.read).length;
  const totalCount = notifications.length;

  return {
    notifications,
    loading,
    error,
    unreadCount,
    totalCount,
    markRead,
    markAllRead,
    refresh,
    startPolling,
    stopPolling,
  };
}

export default useNotifications;
