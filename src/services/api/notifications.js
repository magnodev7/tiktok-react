import api from '@/api/client';

/**
 * Serviço de API para Notificações
 * Utiliza logs do sistema para gerar notificações relevantes
 */

/**
 * Busca notificações do usuário
 * Converte logs relevantes em notificações
 */
export async function getNotifications(params = {}) {
  try {
    const { limit = 20, account = null } = params;

    console.log('[Notifications] Buscando logs...', { limit, account });

    // Busca logs recentes do usuário
    const response = await api.get('/api/logs', {
      params: {
        limit: limit * 2, // Busca mais logs para filtrar os relevantes
        account,
      },
    });

    console.log('[Notifications] Resposta recebida:', response.data);

    const logs = response.data.logs || [];
    console.log('[Notifications] Total de logs recebidos:', logs.length);

    // Converte logs relevantes em notificações
    const notifications = logs
      .filter(log => isRelevantLog(log))
      .map(log => logToNotification(log))
      .slice(0, limit); // Limita ao número solicitado

    console.log('[Notifications] Notificações processadas:', notifications.length);
    console.log('[Notifications] Retornando array de notificações');

    return notifications;
  } catch (error) {
    console.error('[Notifications] Erro ao buscar notificações:', error);
    console.error('[Notifications] Detalhes do erro:', {
      message: error.message,
      response: error.response?.data,
      status: error.response?.status,
    });

    // Retorna array vazio em caso de erro para não travar a UI
    return [];
  }
}

/**
 * Marca notificação como lida
 * (Por enquanto, apenas no frontend - pode ser implementado no backend depois)
 */
export async function markAsRead(notificationId) {
  try {
    // TODO: Implementar endpoint no backend se necessário
    // Por enquanto, gerencia localmente via localStorage
    const readIds = getReadNotifications();
    readIds.add(notificationId);
    localStorage.setItem('readNotifications', JSON.stringify([...readIds]));
    return true;
  } catch (error) {
    console.error('Erro ao marcar notificação como lida:', error);
    return false;
  }
}

/**
 * Marca todas as notificações como lidas
 */
export async function markAllAsRead(notifications) {
  try {
    const readIds = getReadNotifications();
    notifications.forEach(n => readIds.add(n.id));
    localStorage.setItem('readNotifications', JSON.stringify([...readIds]));
    return true;
  } catch (error) {
    console.error('Erro ao marcar todas como lidas:', error);
    return false;
  }
}

/**
 * Busca IDs de notificações já lidas
 */
function getReadNotifications() {
  try {
    const stored = localStorage.getItem('readNotifications');
    return new Set(stored ? JSON.parse(stored) : []);
  } catch {
    return new Set();
  }
}

/**
 * Verifica se um log é relevante para se tornar notificação
 */
function isRelevantLog(log) {
  const message = log.message?.toLowerCase() || '';
  const level = log.level?.toLowerCase() || '';

  // Ignora logs muito genéricos ou de debug
  if (level === 'debug') return false;

  // Logs relevantes para notificações
  const relevantKeywords = [
    'vídeo',
    'postado',
    'sucesso',
    'publicado',
    'agendado',
    'falha',
    'erro',
    'conta',
    'upload',
    'completed',
    'failed',
    'warning',
  ];

  return relevantKeywords.some(keyword => message.includes(keyword));
}

/**
 * Converte log em objeto de notificação
 */
function logToNotification(log) {
  const readIds = getReadNotifications();
  const id = `log-${log.id}`;

  return {
    id,
    title: getNotificationTitle(log),
    message: log.message,
    time: formatTime(log.created_at),
    read: readIds.has(id),
    type: getNotificationType(log.level),
    level: log.level,
    account: log.account_name,
    module: log.module,
  };
}

/**
 * Gera título da notificação baseado no log
 */
function getNotificationTitle(log) {
  const level = log.level?.toLowerCase() || '';
  const message = log.message?.toLowerCase() || '';

  // Títulos baseados em padrões comuns
  if (message.includes('vídeo') && message.includes('postado')) {
    return 'Vídeo publicado com sucesso';
  }
  if (message.includes('vídeo') && message.includes('agendado')) {
    return 'Vídeo agendado';
  }
  if (message.includes('upload') && message.includes('sucesso')) {
    return 'Upload concluído';
  }
  if (message.includes('falha') || level === 'error') {
    return 'Erro na operação';
  }
  if (level === 'warning') {
    return 'Atenção necessária';
  }
  if (message.includes('conta') && message.includes('criada')) {
    return 'Nova conta adicionada';
  }

  // Fallback: usa as primeiras palavras da mensagem
  const words = log.message.split(' ').slice(0, 5).join(' ');
  return words.length < log.message.length ? `${words}...` : words;
}

/**
 * Define tipo visual da notificação
 */
function getNotificationType(level) {
  const levelMap = {
    error: 'error',
    critical: 'error',
    warning: 'warning',
    info: 'info',
    debug: 'info',
  };

  return levelMap[level?.toLowerCase()] || 'info';
}

/**
 * Formata tempo relativo (ex: "5 min atrás")
 */
function formatTime(timestamp) {
  try {
    const now = new Date();
    const date = new Date(timestamp);
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Agora mesmo';
    if (diffMins < 60) return `${diffMins} min atrás`;
    if (diffHours < 24) return `${diffHours}h atrás`;
    if (diffDays === 1) return 'Ontem';
    if (diffDays < 7) return `${diffDays} dias atrás`;

    // Mais de 7 dias: mostra data
    return date.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  } catch {
    return 'Data inválida';
  }
}

export default {
  getNotifications,
  markAsRead,
  markAllAsRead,
};
