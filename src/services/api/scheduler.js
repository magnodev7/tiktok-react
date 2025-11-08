import api from '@/api/client';

/**
 * Recupera o estado do scheduler para as contas do usuário atual.
 * Retorna array de objetos com status, próximos horários e metadados.
 */
export async function getSchedulerStatus({ account } = {}) {
  try {
    const response = await api.get('/api/scheduler/status', {
      params: account ? { account } : undefined,
    });
    return response.data?.data ?? [];
  } catch (error) {
    console.error('[SchedulerStatus] Falha ao consultar estado do scheduler:', error);
    return [];
  }
}
