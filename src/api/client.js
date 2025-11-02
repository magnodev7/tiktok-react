import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8082/',
  timeout: 900000, // 15 minutos para uploads de vídeo grandes (alinhado com Nginx)
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: Adiciona token de autenticação
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    console.log('[API Client] Enviando requisição:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error('[API Client] Erro no request interceptor:', error);
    return Promise.reject(error);
  }
);

// Response interceptor: padroniza payload (success/data/message)
apiClient.interceptors.response.use(
  (response) => {
    console.log('[API Client] Resposta recebida:', response.config.method?.toUpperCase(), response.config.url, '→', response.status);

    const payload = response?.data;
    if (payload && typeof payload === 'object' && Object.prototype.hasOwnProperty.call(payload, 'success')) {
      if (!payload.success) {
        console.warn('[API Client] Payload com success=false recebido', payload);
        const error = new Error(payload.message || 'Erro na operação');
        error.response = { ...response, data: payload };
        error.config = response.config;
        error.status = response.status;
        return Promise.reject(error);
      }

      response.data = payload.data ?? null;
      response.meta = {
        message: payload.message ?? null,
        raw: payload,
      };
    }

    return response;
  },
  (error) => {
    console.error('[API Client] Erro na resposta:', error.config?.method?.toUpperCase(), error.config?.url, '→', error.response?.status || 'Network Error');
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
