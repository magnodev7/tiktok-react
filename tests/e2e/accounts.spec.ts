import { test, expect, Page } from '@playwright/test';
import process from 'process';

const baseUrl = process.env.PLAYWRIGHT_BASE_URL;
const shouldSkip = !baseUrl || process.env.USE_REAL_API === 'false';

const adminUsername = process.env.E2E_USERNAME ?? 'admin';
const adminPassword = process.env.E2E_PASSWORD ?? 'admin';

async function login(page: Page) {
  await page.goto('/login');
  await expect(page.getByPlaceholder('seu_usuario')).toBeVisible();
  await page.getByPlaceholder('seu_usuario').fill(adminUsername);
  await page.getByPlaceholder('••••••••').fill(adminPassword);
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page).toHaveURL('/', { timeout: 15_000 });
}

async function ensureOnAccounts(page: Page) {
  await page.getByRole('link', { name: /Contas TikTok/i }).click();
  await expect(page).toHaveURL('/accounts');
  await expect(page.getByRole('heading', { name: 'Contas TikTok' })).toBeVisible();
}

async function cleanupAccount(page: Page, accountName: string) {
  const card = page.locator(`[data-testid="account-card"][data-account-name="${accountName}"]`);
  if (await card.count()) {
    page.once('dialog', (dialog) => dialog.accept());
    await card.getByRole('button', { name: 'Excluir' }).click();
    await expect(card).toHaveCount(0);
  }
}

test.describe('Gestão de contas (API real)', () => {
  test.skip(shouldSkip, 'Requer backend real configurado (PLAYWRIGHT_BASE_URL) e uso da API real.');

  test.beforeEach(async ({}, testInfo) => {
    const context = testInfo.titlePath.join(' > ');
    console.log(`\n========== Início do teste: ${context} ==========`);
  });

  test.afterEach(async ({}, testInfo) => {
    const context = testInfo.titlePath.join(' > ');
    console.log(`========== Fim do teste: ${context} | Status: ${testInfo.status} ==========`);
  });

  test('usuário cria, edita e exclui uma conta TikTok', async ({ page }) => {
    const accountName = `e2e-${Date.now()}`;
    const updatedDescription = `Conta atualizada via E2E - ${new Date().toISOString()}`;
    let cleanupNeeded = false;

    await login(page);
    await ensureOnAccounts(page);

    try {
      await page.getByRole('button', { name: 'Adicionar Conta' }).click();
      await expect(page.getByRole('heading', { name: 'Adicionar Conta TikTok' })).toBeVisible();

      await page.getByPlaceholder('novadigitalbra (sem @)').fill(accountName);
      await page.getByPlaceholder('••••••••').fill('SenhaSegura@123');

      await page.getByRole('button', { name: 'Conectar Conta' }).click();
      await expect(page.getByRole('heading', { name: 'Adicionar Conta TikTok' })).toBeHidden();

    const card = page.locator(`[data-testid="account-card"][data-account-name="${accountName}"]`);
    await expect(card).toBeVisible({ timeout: 15_000 });
    cleanupNeeded = true;

      await card.getByRole('button', { name: 'Editar' }).click();
      await expect(page.getByRole('heading', { name: 'Editar Conta TikTok' })).toBeVisible();

      await page.getByPlaceholder('Descrição da conta...').fill(updatedDescription);
      await page.getByRole('button', { name: 'Salvar Alterações' }).click();
      await expect(page.getByRole('heading', { name: 'Editar Conta TikTok' })).toBeHidden();

      await expect(card.getByText(updatedDescription, { exact: false })).toBeVisible({ timeout: 10_000 });

      page.once('dialog', (dialog) => dialog.accept());
      await card.getByRole('button', { name: 'Excluir' }).click();
      await expect(card).toHaveCount(0);
      cleanupNeeded = false;
    } finally {
      if (cleanupNeeded) {
        await ensureOnAccounts(page);
        await cleanupAccount(page, accountName);
      }
    }
  });
});
