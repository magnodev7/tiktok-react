import { http, HttpResponse } from 'msw';
import {
  mockAccounts,
  mockAnalytics,
  mockCapacity,
  mockCapacityAlerts,
  mockLogs,
  mockScheduledVideos,
  mockUser,
} from './fixtures';

const API_BASE = 'http://localhost:8082';

const success = (data, message = null) =>
  HttpResponse.json({
    success: true,
    message,
    data,
  });

export const handlers = [
  http.post(`${API_BASE}/auth/login`, async () => {
    return success({
      access_token: 'mock-token',
      token_type: 'bearer',
      user: mockUser,
    });
  }),

  http.get(`${API_BASE}/auth/me`, async ({ request }) => {
    const auth = request.headers.get('Authorization');
    if (!auth) {
      return HttpResponse.json({ detail: 'Unauthorized' }, { status: 401 });
    }
    return success(mockUser);
  }),

  http.get(`${API_BASE}/api/tiktok-accounts`, async () => {
    return success(mockAccounts);
  }),

  http.get(`${API_BASE}/api/scheduled`, async ({ request }) => {
    const url = new URL(request.url);
    const account = url.searchParams.get('account');
    if (!account) {
      return success({ scheduled_videos: [] });
    }
    return success({ scheduled_videos: mockScheduledVideos });
  }),

  http.get(`${API_BASE}/api/analytics/summary`, async () => {
    return success(mockAnalytics);
  }),

  http.get(`${API_BASE}/api/posting-schedules/:accountId/capacity`, async () => {
    return success(mockCapacity);
  }),

  http.get(`${API_BASE}/api/posting-schedules/:accountId/alerts`, async () => {
    return success(mockCapacityAlerts);
  }),

  http.get(`${API_BASE}/api/logs`, async () => {
    return success({ logs: mockLogs });
  }),
];
