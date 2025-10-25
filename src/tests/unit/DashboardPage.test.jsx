import { describe, expect, it, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import Dashboard from '@/pages/Dashboard';
import { renderWithProviders } from '../utils';

describe('Dashboard page', () => {
  beforeEach(() => {
    localStorage.setItem('auth_token', 'mock-token');
  });

  it('exibe métricas, vídeos e widget de capacidade', async () => {
    renderWithProviders(<Dashboard />);

    await waitFor(() => {
      expect(screen.getAllByText(/vídeos agendados/i).length).toBeGreaterThan(0);
    });

    expect(screen.getByText('Vídeos Agendados')).toBeInTheDocument();
    expect(screen.getByText('Vídeos Postados (7d)')).toBeInTheDocument();
    expect(screen.getByText(/video-lancamento\.mp4/i)).toBeInTheDocument();
  });
});
