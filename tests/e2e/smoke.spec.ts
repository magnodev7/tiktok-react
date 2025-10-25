import { test, expect, Page } from '@playwright/test';
import process from 'process';

const useRealApi = process.env.USE_REAL_API !== 'false';
const testUsername = process.env.E2E_USERNAME ?? 'admin';
const testPassword = process.env.E2E_PASSWORD ?? 'admin';

const isApiRequest = (url: string) => {
  try {
    const { pathname } = new URL(url);
    return pathname.startsWith('/auth/') || pathname.startsWith('/api/');
  } catch {
    return false;
  }
};

const mockUser = {
  id: 1,
  username: 'admin',
  full_name: 'Administrador',
  is_admin: true,
};

const mockAccounts = [
  { id: 1, account_name: 'autegra', display_name: 'Autegra Oficial', is_active: true },
];

const mockScheduled = [
  {
    id: 100,
    video_path: 'video-lancamento.mp4',
    description: 'Campanha principal',
    account: 'autegra',
    when: '2025-01-05T15:00:00Z',
    status: 'scheduled',
  },
];

const mockAnalytics = {
  overview: {
    total_videos: 10,
    posted: 4,
  },
  daily_stats: {
    '2025-01-02': 1,
    '2025-01-03': 2,
    '2025-01-04': 1,
  },
};

const mockCapacity = {
  daily_capacity: 5,
  total_occupied: 6,
  total_capacity: 25,
  percentage_full: 24,
  days_until_full: 9,
  time_slots: ['09:00', '11:00', '13:00'],
};

const mockAlerts = [
  {
    alert_type: 'info',
    message: 'Nenhum risco identificado nos próximos dias',
  },
];

const mockLogs = [
  {
    id: 1,
    message: 'Vídeo agendado com sucesso',
    level: 'info',
    created_at: '2025-01-04T10:00:00Z',
    account_name: 'autegra',
    module: 'scheduler',
  },
];

async function registerApiMocks(page: Page) {
  await page.route('**/*', async (route) => {
    const request = route.request();
    if (!isApiRequest(request.url())) {
      await route.continue();
      return;
    }

    const url = new URL(request.url());
    const { pathname } = url;

    console.log('API request captured:', request.method(), pathname);

    if (request.method() === 'OPTIONS') {
      await route.fulfill({
        status: 204,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Headers': 'Authorization, Content-Type',
          'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        },
        body: '',
      });
      return;
    }

    if (pathname === '/auth/login' && request.method() === 'POST') {
      console.log('Intercepting login request with body:', await request.postData());
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: { 'Access-Control-Allow-Origin': '*' },
        body: JSON.stringify({
          success: true,
          data: {
            access_token: 'mock-token',
            token_type: 'bearer',
            user: mockUser,
          },
        }),
      });
      return;
    }

    if (pathname === '/auth/me' && request.method() === 'GET') {
      const authHeader = request.headers()['authorization'];
      if (!authHeader) {
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          headers: { 'Access-Control-Allow-Origin': '*' },
          body: JSON.stringify({ detail: 'Unauthorized' }),
        });
        return;
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: { 'Access-Control-Allow-Origin': '*' },
        body: JSON.stringify({ success: true, data: mockUser }),
      });
      return;
    }

    if (pathname === '/api/tiktok-accounts' && request.method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: { 'Access-Control-Allow-Origin': '*' },
        body: JSON.stringify({ success: true, data: mockAccounts }),
      });
      return;
    }

    if (pathname === '/api/scheduled' && request.method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: { 'Access-Control-Allow-Origin': '*' },
        body: JSON.stringify({ success: true, data: { scheduled_videos: mockScheduled } }),
      });
      return;
    }

    if (pathname === '/api/analytics/summary' && request.method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: { 'Access-Control-Allow-Origin': '*' },
        body: JSON.stringify({ success: true, data: mockAnalytics }),
      });
      return;
    }

    if (pathname.endsWith('/capacity') && request.method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: { 'Access-Control-Allow-Origin': '*' },
        body: JSON.stringify({ success: true, data: mockCapacity }),
      });
      return;
    }

    if (pathname.endsWith('/alerts') && request.method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: { 'Access-Control-Allow-Origin': '*' },
        body: JSON.stringify({ success: true, data: mockAlerts }),
      });
      return;
    }

    if (pathname === '/api/logs' && request.method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: { 'Access-Control-Allow-Origin': '*' },
        body: JSON.stringify({ success: true, data: { logs: mockLogs } }),
      });
      return;
    }

    await route.fulfill({
      status: 404,
      contentType: 'application/json',
      headers: { 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({ success: false, error: 'not_mocked', path: pathname }),
    });
  });
}

test.describe('Fluxo principal do painel', () => {
  test.beforeEach(async ({}, testInfo) => {
    const context = testInfo.titlePath.join(' > ');
    console.log(`\n========== Início do teste: ${context} ==========`);
  });

  test.afterEach(async ({}, testInfo) => {
    const context = testInfo.titlePath.join(' > ');
    console.log(`========== Fim do teste: ${context} | Status: ${testInfo.status} ==========`);
  });

  test.beforeEach(async ({ page }) => {
    if (!useRealApi) {
      await registerApiMocks(page);
      page.on('request', (req) => {
        if (isApiRequest(req.url())) {
          console.log('Network request out:', req.method(), req.url());
        }
      });
    }

    page.on('console', (msg) => {
      console.log(`[console:${msg.type()}]`, msg.text());
    });
  });

  test('usuário realiza login e navega pelo dashboard', async ({ page }) => {
    await page.goto('/login');

    await expect(page.getByPlaceholder('seu_usuario')).toBeVisible({ timeout: 15_000 });

    await page.getByPlaceholder('seu_usuario').fill(testUsername);
    await page.getByPlaceholder('••••••••').fill(testPassword);
    await page.getByRole('button', { name: 'Entrar' }).click();

    // Aceita "/" ou "/dashboard" em qualquer host
    await expect(page).toHaveURL(/\/(?:dashboard)?\/?$/, { timeout: useRealApi ? 20_000 : 10_000 });

    // Aguarda qualquer sinal robusto de prontidão no dashboard (heading/analytics/indicadores)
    await expect
      .poll(async () => {
        const headingCount = await page.getByRole('main').getByRole('heading', { name: 'Dashboard' }).count();
        const analyticsCount = await page.locator('[data-testid="analytics-overview"], [data-testid="analytics-summary"], [class*="analytics"]').count();
        const contasAtivasCount = await page.getByText('Contas Ativas').count();
        return headingCount > 0 || analyticsCount > 0 || contasAtivasCount > 0;
      }, { timeout: 20_000, intervals: [300, 700, 1200] })
      .toBe(true);

    // Assertivas com auto-retry e timeouts locais
    const dashboardHeading = page.getByRole('main').getByRole('heading', { name: 'Dashboard' });
    if (await dashboardHeading.count()) {
      await expect(dashboardHeading).toBeVisible({ timeout: 20_000 });
    }
    await expect(page.getByText('Contas Ativas')).toBeVisible({ timeout: 15_000 });

    const noVideosHeading = page.getByRole('heading', { name: 'Nenhum vídeo agendado' });
    if ((await noVideosHeading.count()) > 0) {
      await expect(noVideosHeading).toBeVisible({ timeout: 10_000 });
    } else {
      await expect(page.getByText('Agendado', { exact: false }).first()).toBeVisible({ timeout: 10_000 });
    }

    await page.getByRole('link', { name: /Contas TikTok/i }).click();
    await expect(page).toHaveURL('/accounts', { timeout: 10_000 });
    await expect(page.getByRole('heading', { name: 'Contas TikTok' })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('Total de Contas')).toBeVisible({ timeout: 10_000 });
  });
});
