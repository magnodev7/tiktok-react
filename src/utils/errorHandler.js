// Toast instance will be set by the app
let toastInstance = null;

export function setToastInstance(toast) {
  toastInstance = toast;
}

// Sanitize message to prevent XSS
function sanitizeMessage(message) {
  if (typeof message !== 'string') {
    return 'Erro desconhecido';
  }

  // Remove HTML tags and limit length
  const sanitized = message
    .replace(/<[^>]*>/g, '')
    .trim()
    .substring(0, 500);

  return sanitized || 'Erro desconhecido';
}

export function handleApiError(error) {
  if (error.response) {
    const status = error.response.status;
    const rawMessage = error.response.data?.message || error.response.data?.error || 'Erro desconhecido';
    const message = sanitizeMessage(rawMessage);

    const errorMessages = {
      400: `Requisição inválida: ${message}`,
      401: 'Sessão expirada. Faça login novamente.',
      403: 'Você não tem permissão para esta ação.',
      404: 'Recurso não encontrado.',
      500: 'Erro no servidor. Tente novamente mais tarde.',
    };

    return errorMessages[status] || message;
  } else if (error.request) {
    return 'Sem conexão com o servidor. Verifique sua internet.';
  } else {
    return 'Erro inesperado. Tente novamente.';
  }
}

export function showError(error) {
  const message = handleApiError(error);

  // Show toast notification if available
  if (toastInstance) {
    toastInstance.error(message);
  } else {
    console.error('[Toast não inicializado]', message);
  }

  return message;
}

export function showSuccess(message) {
  const sanitized = sanitizeMessage(message);

  if (toastInstance) {
    toastInstance.success(sanitized);
  } else {
    console.log('[Toast não inicializado]', sanitized);
  }
}

export function showWarning(message) {
  const sanitized = sanitizeMessage(message);

  if (toastInstance) {
    toastInstance.warning(sanitized);
  } else {
    console.warn('[Toast não inicializado]', sanitized);
  }
}

export function showInfo(message) {
  const sanitized = sanitizeMessage(message);

  if (toastInstance) {
    toastInstance.info(sanitized);
  } else {
    console.info('[Toast não inicializado]', sanitized);
  }
}
