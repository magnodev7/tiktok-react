import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from '@/contexts/AuthContext';
import { SelectedAccountProvider } from '@/contexts/SelectedAccountContext';
import { ToastProvider } from '@/components/common/ToastContainer';
import { setToastInstance } from '@/utils/errorHandler';
import Layout from '@/components/layout/Layout';
import Login from '@/pages/Login';
import Register from '@/pages/Register';
import Dashboard from '@/pages/Dashboard';
import Accounts from '@/pages/Accounts';
import PostingSchedules from '@/pages/PostingSchedules';
import Analytics from '@/pages/Analytics';
import Settings from '@/pages/Settings';
import Logs from '@/pages/Logs';
import AccountGrowth from '@/pages/AccountGrowth';
import Maintenance from '@/pages/Maintenance';
import Spinner from '@/components/common/Spinner';
import ToastInitializer from '@/components/common/ToastInitializer';
import '@/styles/animations.css';

// React Query Client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000, // 1 minute
      cacheTime: 5 * 60 * 1000, // 5 minutes
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

// Protected Route Component
function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

// Public Route Component (redirect if authenticated)
function PublicRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Spinner size="lg" />
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return children;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <HashRouter>
        <AuthProvider>
          <SelectedAccountProvider>
            <ToastProvider>
              <ToastInitializer />
              <Routes>
                {/* Public Routes */}
                <Route
                  path="/login"
                  element={
                    <PublicRoute>
                      <Login />
                    </PublicRoute>
                  }
                />
                <Route
                  path="/register"
                  element={
                    <PublicRoute>
                      <Register />
                    </PublicRoute>
                  }
                />

                {/* Protected Routes */}
                <Route
                  path="/"
                  element={
                    <ProtectedRoute>
                      <Layout />
                    </ProtectedRoute>
                  }
                >
                  <Route index element={<Dashboard />} />
                  <Route path="accounts" element={<Accounts />} />
                  <Route path="schedules" element={<PostingSchedules />} />
                  <Route path="growth" element={<AccountGrowth />} />
                  <Route path="analytics" element={<Analytics />} />
                  <Route path="logs" element={<Logs />} />
                  <Route path="maintenance" element={<Maintenance />} />
                  <Route path="settings" element={<Settings />} />
                </Route>

                {/* 404 */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </ToastProvider>
          </SelectedAccountProvider>
        </AuthProvider>
      </HashRouter>
    </QueryClientProvider>
  );
}

export default App;
