export const mockUser = {
  id: 1,
  username: 'admin',
  full_name: 'Administrador',
  email: 'admin@example.com',
  is_admin: true,
  profile_picture: null,
};

export const mockAccounts = [
  {
    id: 1,
    account_name: 'autegra',
    display_name: 'Autegra Oficial',
    is_active: true,
  },
  {
    id: 2,
    account_name: 'backup',
    display_name: 'Backup',
    is_active: false,
  },
];

export const mockScheduledVideos = [
  {
    id: 10,
    video_path: 'video-lancamento.mp4',
    description: 'Campanha principal da semana',
    account: 'autegra',
    when: '2025-01-05T15:00:00Z',
    status: 'scheduled',
  },
  {
    id: 11,
    video_path: 'video-bastidores.mp4',
    description: 'Bastidores da última gravação',
    account: 'autegra',
    when: '2025-01-06T18:30:00Z',
    status: 'scheduled',
  },
];

export const mockAnalytics = {
  overview: {
    total_videos: 20,
    posted: 12,
  },
  daily_stats: {
    '2025-01-03': 3,
    '2025-01-04': 1,
    '2025-01-05': 4,
    '2025-01-06': 2,
  },
};

export const mockCapacity = {
  daily_capacity: 5,
  total_occupied: 8,
  total_capacity: 25,
  percentage_full: 32,
  days_until_full: 7,
  time_slots: ['09:00', '11:00', '13:00', '15:00', '17:00'],
};

export const mockCapacityAlerts = [
  {
    alert_type: 'info',
    message: 'Capacidade saudável para os próximos 7 dias',
  },
];

export const mockLogs = [
  {
    id: 500,
    message: 'Vídeo agendado com sucesso',
    level: 'info',
    created_at: '2025-01-04T12:00:00Z',
    account_name: 'autegra',
    module: 'scheduler',
  },
];
