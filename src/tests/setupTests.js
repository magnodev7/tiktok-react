import '@testing-library/jest-dom/vitest';
import { afterAll, afterEach, beforeAll, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import { server } from './testServer';

// Inicia o MSW antes dos testes
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));

// Limpa mocks e estado após cada teste
afterEach(() => {
  cleanup();
  server.resetHandlers();
  localStorage.clear();
  sessionStorage.clear();
});

// Encerra o MSW após todos os testes
afterAll(() => server.close());

// Mock global minimal para matchMedia utilizado por alguns componentes
if (!window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(), // Deprecated
      removeListener: vi.fn(), // Deprecated
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
}

// Evita chamadas reais nas notificações (polling)
vi.mock('@/hooks/useNotifications', () => ({
  useNotifications: () => ({
    notifications: [],
    loading: false,
    error: null,
    unreadCount: 0,
    totalCount: 0,
    markRead: vi.fn(),
    markAllRead: vi.fn(),
    refresh: vi.fn(),
    startPolling: vi.fn(),
    stopPolling: vi.fn(),
  }),
}));
