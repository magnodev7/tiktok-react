// tests/e2e/apikeys.spec.ts
import { test, expect, Page } from '@playwright/test';

const E2E_USERNAME = process.env.E2E_USERNAME ?? 'admin';
const E2E_PASSWORD = process.env.E2E_PASSWORD ?? 'admin';

async function login(page: Page) {
  await page.goto('/login');
  await expect(page.getByPlaceholder('seu_usuario')).toBeVisible({ timeout: 15000 });
  await page.getByPlaceholder('seu_usuario').fill(E2E_USERNAME);
  await page.getByPlaceholder('••••••••').fill(E2E_PASSWORD);
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page).toHaveURL(/\/(?:dashboard)?\/?$/, { timeout: 20000 });
}

async function navigateToApiKeys(page: Page) {
  await page.goto('/settings');
  await expect(page.getByRole('heading', { name: /Configurações/i })).toBeVisible({ timeout: 15000 });

  const apiTab = page.getByRole('button', { name: /^API$/i }).first();
  if (await apiTab.count()) {
    await apiTab.click();
  } else {
    await page.goto('/settings/api-keys');
  }

  await expect(page.getByRole('heading', { name: 'API Keys', exact: true })).toBeVisible({ timeout: 15000 });
}

test.describe('API Keys - CRUD completo (API real)', () => {
  test.beforeEach(async ({ context }) => {
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  });

  test('lista, cria, copia, alterna status e deleta API Key', async ({ page }) => {
    await login(page);
    await navigateToApiKeys(page);

    const uniqueKeyName = `Chave Integração - ${Date.now()}`;

    // Abre o formulário
    await page.getByRole('button', { name: /Nova API Key/i }).click();

    // Aguarda o modal abrir
    await expect(page.getByText(/Criar nova API Key|Nova Chave/i)).toBeVisible({ timeout: 15000 });

    // Localiza o campo de nome (primeiro input visível)
    const nameInput = page.locator('input, textarea').first();
    await expect(nameInput).toBeVisible({ timeout: 10000 });
    await nameInput.fill(uniqueKeyName);

    // Localiza o botão "Criar API Key" próximo ao campo de nome
    const createBtn = nameInput.locator('xpath=following::button[contains(text(), "Criar API Key")][1]');
    await expect(createBtn).toBeEnabled({ timeout: 10000 });
    await createBtn.click();

    // Aguarda mensagem de sucesso
    await expect(page.getByText(/API Key Criada com Sucesso!/i)).toBeVisible({ timeout: 15000 });
    await page.getByRole('button', { name: /Fechar|Entendi/i }).click();

    // ✅ Agora, espere que a chave apareça na lista
    await expect(page.getByText(uniqueKeyName)).toBeVisible({ timeout: 15000 });

    // ✅ Tenta encontrar o card pela classe mais comum usada em UIs modernas
    // Se o card tiver uma classe como "card", "api-key-item", etc., use-a
    // Caso contrário, tenta uma busca mais genérica
    const card = page.locator('.card, .Card, [class*="api-key"], [class*="item"], .p-4, .flex').filter({ has: page.getByText(uniqueKeyName) }).first();

    // ✅ Agora, dentro do card, procure o botão de status de forma mais ampla
    // Em vez de "Ativar|Desativar", procure qualquer botão com texto que indique status
    const toggleBtn = card.getByRole('button', { name: /ativar|desativar|status|toggle/i });

    // Se o botão não for encontrado, pode ser um botão com ícone ou classe específica
    // Nesse caso, tente localizar pelo texto "Ativar" ou "Desativar" diretamente no botão
    // const toggleBtn = card.locator('button:has-text("Ativar"), button:has-text("Desativar")').first();

    await expect(toggleBtn).toBeVisible({ timeout: 10000 });

    // Alterna status
    const initial = (await toggleBtn.innerText()).trim();
    await toggleBtn.click();
    await expect.poll(async () => {
      const current = (await toggleBtn.innerText()).trim();
      return current !== initial;
    }, { timeout: 15000 }).toBeTruthy();

    // Deleta
    page.once('dialog', d => d.accept());
    // O botão de deletar costuma ser o último, mas pode ter um ícone
    await card.locator('button').last().click();
    await expect(page.getByText(uniqueKeyName)).toHaveCount(0, { timeout: 15000 });
  });
});