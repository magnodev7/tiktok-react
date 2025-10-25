import { test, expect, Page, Locator } from '@playwright/test';
import * as fs from 'fs';

const baseUrl = process.env.PLAYWRIGHT_BASE_URL;
const shouldSkip = !baseUrl || process.env.USE_REAL_API === 'false';

const adminUsername = process.env.E2E_USERNAME ?? 'admin';
const adminPassword = process.env.E2E_PASSWORD ?? 'admin';

async function login(page: Page) {
  await page.goto('/login', { waitUntil: 'load' });
  await expect(page.getByPlaceholder('seu_usuario')).toBeVisible({ timeout: 30_000 });
  await page.getByPlaceholder('seu_usuario').fill(adminUsername);
  await page.getByPlaceholder('••••••••').fill(adminPassword);
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page).toHaveURL('/', { timeout: 15_000 });
}

async function ensureLoggedIn(page: Page) {
  if (await page.getByPlaceholder('seu_usuario').count()) {
    await login(page);
  }
}

async function goToAccounts(page: Page) {
  const link = page.getByRole('link', { name: /Contas TikTok/i });
  if (await link.count()) {
    await link.click();
  } else {
    await page.goto('/accounts', { waitUntil: 'load' });
  }
  await expect(page).toHaveURL(/\/accounts(?:$|\/|\?)/, { timeout: 15_000 });
  await expect(page.getByRole('heading', { name: 'Contas TikTok' })).toBeVisible({ timeout: 15_000 });
}

async function createAccount(page: Page, accountName: string) {
  await page.getByRole('button', { name: 'Adicionar Conta' }).click();
  await expect(page.getByRole('heading', { name: 'Adicionar Conta TikTok' })).toBeVisible({ timeout: 15_000 });

  await page.getByPlaceholder('novadigitalbra (sem @)').fill(accountName);
  await page.getByPlaceholder('••••••••').fill('SenhaSegura@123');

  await page.getByRole('button', { name: 'Conectar Conta' }).click();
  await expect(page.getByRole('heading', { name: 'Adicionar Conta TikTok' })).toBeHidden({ timeout: 15_000 });

  const card = page.locator(
    `[data-testid="account-card"][data-account-name="${accountName}"]`
  );
  await expect(card).toBeVisible({ timeout: 15_000 });
}

async function deleteAccount(page: Page, accountName: string) {
  const card = page.locator(
    `[data-testid="account-card"][data-account-name="${accountName}"]`
  );
  if (await card.count()) {
    page.once('dialog', (dialog) => dialog.accept());
    await card.getByRole('button', { name: 'Excluir' }).click();
    await expect(card).toHaveCount(0);
  }
}

async function goToSchedules(page: Page) {
  const link = page.getByRole('link', { name: /Agendamentos/i });
  if (await link.count()) {
    await link.click();
  } else {
    await page.goto('/schedules', { waitUntil: 'load' });
  }
  await expect(page).toHaveURL(/\/schedules(?:$|\/|\?)/, { timeout: 15_000 });
  await expect(page.getByRole('heading', { name: 'Horários de Postagem' })).toBeVisible({ timeout: 30_000 });
}

async function getCurrentSlots(page: Page) {
  const elements = await page.locator('[data-testid="time-slot"]').all();
  const slots: string[] = [];
  for (const el of elements) {
    const value = await el.getAttribute('data-time');
    if (value) {
      slots.push(value);
    }
  }
  return slots.sort();
}

// Localiza uma ação de "Salvar", se existir; retorna o Locator ou null
async function findSaveAction(page: Page): Promise<Locator | null> {
  const candidates: Locator[] = [
    page.getByRole('button', { name: /salvar alterações/i }),
    page.getByRole('button', { name: /salvar/i }),
    page.getByRole('link', { name: /salvar/i }),
    page.getByLabel(/salvar/i),
    page.locator('[role="button"]', { hasText: /salvar/i }),
    page.locator('button').filter({ hasText: /salvar/i }),
    page.getByTestId('floating-save-button'),
    page.getByTestId('banner-save-button'),
    page.getByTestId('save-schedules'),
    page.locator('form button[type="submit"]'),
    page.locator('[data-testid="actions"] button', { hasText: /salvar/i }),
  ];

  await page.mouse.wheel(0, 2000);
  for (const c of candidates) {
    try {
      if (await c.first().isVisible({ timeout: 1000 })) {
        return c.first();
      }
    } catch {
      // tenta próximo
    }
  }
  return null;
}

// Aguarda persistência: modo 'subset' permite extras no DOM; 'exact' exige igualdade
async function waitForPersistence(
  page: Page,
  expectedSlots: string[],
  mode: 'subset' | 'exact' = 'exact'
) {
  const expectedSorted = [...expectedSlots].sort();

  await Promise.race([
    page
      .waitForResponse(
        (res) =>
          res.url().includes('/schedules') &&
          ['PUT', 'POST', 'PATCH'].includes(res.request().method()) &&
          res.ok(),
        { timeout: 15_000 }
      )
      .catch(() => null),
    page.getByText(/✓\s*Salvo/i).waitFor({ state: 'visible', timeout: 15_000 }).catch(() => null),
    (async () => {
      if (mode === 'exact') {
        await expect
          .poll(async () => await getCurrentSlots(page), {
            timeout: 15_000,
            intervals: [400, 700, 1000, 1500],
          })
          .toEqual(expectedSorted);
      } else {
        await expect
          .poll(async () => {
            const current = await getCurrentSlots(page);
            return expectedSorted.every((s) => current.includes(s));
          }, { timeout: 15_000, intervals: [400, 700, 1000, 1500] })
          .toBe(true);
      }
    })(),
  ]);

  const finalSlots = await getCurrentSlots(page);
  if (mode === 'exact') {
    expect(finalSlots).toEqual(expectedSorted);
  } else {
    for (const s of expectedSorted) {
      expect(finalSlots).toContain(s);
    }
  }
}

test.describe('Horários de postagem (API real)', () => {
  test.describe.configure({ mode: 'serial' });
  test.skip(shouldSkip, 'Requer backend real configurado (PLAYWRIGHT_BASE_URL) e uso da API real.');

  test.beforeEach(async ({}, testInfo) => {
    const context = testInfo.titlePath.join(' > ');
    // eslint-disable-next-line no-console
    console.log(`\n========== Início do teste: ${context} ==========`);
  });

  test.afterEach(async ({}, testInfo) => {
    const context = testInfo.titlePath.join(' > ');
    // eslint-disable-next-line no-console
    console.log(
      `========== Fim do teste: ${context} | Status: ${testInfo.status} ==========`
    );
  });

  test('usuário configura e salva horários de postagem', async ({ page }) => {
    test.setTimeout(120_000);

    const accountName = `sched-${Date.now()}`;
    const manualSlots = ['08:00', '12:00'];
    const presetSlots = Array.from({ length: 8 }, (_, i) => `${String(i * 3).padStart(2, '0')}:00`);
    const finalManualSlots = ['10:30', '18:30'];
    let cleanupNeeded = false;

    await login(page);
    await goToAccounts(page);

    try {
      await createAccount(page, accountName);
      cleanupNeeded = true;

      await goToSchedules(page);

      // Seleciona a conta recém-criada
      let accountSelect = page.getByRole('combobox').first().or(page.locator('select').first());
      await accountSelect.waitFor({ state: 'visible', timeout: 15_000 });
      await accountSelect.selectOption({ label: `@${accountName}` });

      const slotCards = page.locator('[data-testid="time-slot"]');
      const clearButton = page.getByRole('button', { name: 'Limpar Todos' });
      const timeInput = page.locator('input[type="time"]');

      // Salvar se houver botão; caso contrário, esperar autosave/persistência
      const saveOrAutoPersist = async (expectedSlots: string[], mode: 'subset' | 'exact') => {
        const saveButton = await findSaveAction(page);

        if (saveButton) {
          const responseWait = page
            .waitForResponse(
              (res) =>
                res.url().includes('/schedules') &&
                ['PUT', 'POST', 'PATCH'].includes(res.request().method()) &&
                res.ok(),
              { timeout: 15_000 }
            )
            .catch(() => null);

          await saveButton.click({ timeout: 15_000 });

          await Promise.race([
            responseWait,
            page.getByText(/✓\s*Salvo/i).waitFor({ state: 'visible', timeout: 15_000 }),
            (async () => {
              if (mode === 'exact') {
                await expect
                  .poll(async () => await getCurrentSlots(page), {
                    timeout: 15_000,
                    intervals: [400, 700, 1000, 1500],
                  })
                  .toEqual([...expectedSlots].sort());
              } else {
                await expect
                  .poll(async () => {
                    const current = await getCurrentSlots(page);
                    return expectedSlots.every((s) => current.includes(s));
                  }, { timeout: 15_000, intervals: [400, 700, 1000, 1500] })
                  .toBe(true);
              }
            })(),
          ]);
        } else {
          await waitForPersistence(page, expectedSlots, mode);
        }

        const finalSlots = await getCurrentSlots(page);
        if (mode === 'exact') {
          expect(finalSlots).toEqual([...expectedSlots].sort());
        } else {
          for (const s of expectedSlots) expect(finalSlots).toContain(s);
        }
      };

      const clearAllSlots = async () => {
        if (await slotCards.count()) {
          page.once('dialog', (dialog) => dialog.accept());
          await clearButton.click();
          await expect(slotCards).toHaveCount(0);
        }
      };

      await clearAllSlots();

      // === Passo 1: Adicionar horários manuais === (aceita extras por autosave: subset)
      for (const slot of manualSlots) {
        await timeInput.fill(slot);
        await page.getByRole('button', { name: 'Adicionar' }).click();
        await expect(page.locator(`[data-testid="time-slot"][data-time="${slot}"]`)).toBeVisible({
          timeout: 10_000,
        });
      }
      await saveOrAutoPersist(manualSlots, 'subset');

      // === Passo 2: Usar preset "A cada 3h" === (deve substituir: exact)
      await page.getByRole('button', { name: /A cada 3h/ }).click();
      await expect(slotCards).toHaveCount(presetSlots.length, { timeout: 10_000 });
      await saveOrAutoPersist(presetSlots, 'exact');

      // === Passo 3: Configuração final manual === (limpa e define: exact)
      await clearAllSlots();
      for (const slot of finalManualSlots) {
        await timeInput.fill(slot);
        await page.getByRole('button', { name: 'Adicionar' }).click();
        await expect(page.locator(`[data-testid="time-slot"][data-time="${slot}"]`)).toBeVisible({
          timeout: 10_000,
        });
      }
      await saveOrAutoPersist(finalManualSlots, 'exact');

      // === Validação de persistência ===
      const dashLink = page.getByRole('link', { name: /Dashboard/i });
      if (await dashLink.count()) {
        await dashLink.click();
      } else {
        await page.goto('/', { waitUntil: 'load' });
      }
      await page.waitForLoadState('load');
      await goToSchedules(page);

      accountSelect = page.getByRole('combobox').first().or(page.locator('select').first());
      await accountSelect.waitFor({ state: 'visible', timeout: 15_000 });
      await accountSelect.selectOption({ label: `@${accountName}` });
      const ownSlotsBefore = await getCurrentSlots(page);
      expect(ownSlotsBefore).toEqual([...finalManualSlots].sort());

      // === Validação de isolamento entre contas ===
      const nativeSelect = page.locator('select').first();
      if (await nativeSelect.count()) {
        const otherOption = nativeSelect.locator('option', { hasText: '@novadigitalbra' });
        if (await otherOption.count()) {
          // Troca para outra conta
          const waitOtherResp = page
            .waitForResponse(
              (res) =>
                res.url().includes('/schedules') &&
                res.request().method() === 'GET' &&
                res.ok(),
              { timeout: 10_000 }
            )
            .catch(() => null);

          await nativeSelect.selectOption({ label: '@novadigitalbra' });

          // Aguarda atualização por rede ou mudança observável dos slots
          await Promise.race([
            waitOtherResp,
            expect
              .poll(async () => {
                const curr = await getCurrentSlots(page);
                return JSON.stringify(curr) !== JSON.stringify(ownSlotsBefore);
              }, { timeout: 10_000, intervals: [300, 700, 1200] })
              .toBe(true),
          ]);

          // Volta para a conta criada e valida persistência exata
          const waitOwnResp = page
            .waitForResponse(
              (res) =>
                res.url().includes('/schedules') &&
                res.request().method() === 'GET' &&
                res.ok(),
              { timeout: 10_000 }
            )
            .catch(() => null);

          await nativeSelect.selectOption({ label: `@${accountName}` });

          await Promise.race([
            waitOwnResp,
            expect
              .poll(async () => {
                const curr = await getCurrentSlots(page);
                return JSON.stringify(curr) === JSON.stringify([...finalManualSlots].sort());
              }, { timeout: 10_000, intervals: [300, 700, 1200] })
              .toBe(true),
          ]);

          expect(await getCurrentSlots(page)).toEqual([...finalManualSlots].sort());
        }
      }
    } finally {
      if (cleanupNeeded && !page.isClosed()) {
        try {
          await ensureLoggedIn(page);
          await page.goto('/accounts', { waitUntil: 'load' });
          await deleteAccount(page, accountName);
        } catch (cleanupError) {
          // eslint-disable-next-line no-console
          console.warn('[Schedules] Falha ao limpar conta temporária:', cleanupError);
        }
      }
    }
  });
});
