import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '@/contexts/AuthContext';
import { SelectedAccountProvider } from '@/contexts/SelectedAccountContext';

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        cacheTime: 0,
      },
    },
  });
}

export function renderWithProviders(ui, options = {}) {
  const {
    route = '/',
    initialEntries = [route],
    withRouter = true,
    wrapProviders = true,
  } = options;

  if (!wrapProviders) {
    return render(ui);
  }

  const queryClient = createTestQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <SelectedAccountProvider>
          {withRouter ? (
            <MemoryRouter initialEntries={initialEntries}>
              {ui}
            </MemoryRouter>
          ) : (
            ui
          )}
        </SelectedAccountProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
