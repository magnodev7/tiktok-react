#!/usr/bin/env node

/**
 * Gera assinaturas X-Bogus utilizando o script oficial do TikTok (acrawler).
 *
 * Uso:
 *   node tiktok_signer.js "<url_com_query>" "<userAgent>"
 *
 * Saída:
 *   Imprime no stdout o valor da assinatura X-Bogus.
 */

const fs = require('fs');
const path = require('path');
const https = require('https');
const vm = require('vm');
const crypto = require('crypto');

const DEFAULT_USER_AGENT =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';

const ACRAWLER_URL =
  'https://sf16-website-login.neutral.ttwstatic.com/obj/tiktok_web_login_static/webmssdk/1.0.0.316/webmssdk.js';

const cacheDir = path.join(__dirname, '.cache');
const cacheFile = path.join(cacheDir, 'acrawler.js');

function download(url) {
  return new Promise((resolve, reject) => {
    https
      .get(url, (res) => {
        if (res.statusCode !== 200) {
          reject(new Error(`HTTP ${res.statusCode} ao baixar ${url}`));
          res.resume();
          return;
        }
        let data = '';
        res.setEncoding('utf8');
        res.on('data', (chunk) => {
          data += chunk;
        });
        res.on('end', () => resolve(data));
      })
      .on('error', reject);
  });
}

async function ensureAcrawlerScript() {
  if (fs.existsSync(cacheFile)) {
    return fs.readFileSync(cacheFile, 'utf8');
  }

  const script = await download(ACRAWLER_URL);
  fs.mkdirSync(cacheDir, { recursive: true });
  fs.writeFileSync(cacheFile, script, 'utf8');
  return script;
}

function createSandbox(urlToSign, userAgent) {
  const noop = () => {};
  const elementStub = () => ({
    getContext: () => ({}),
    toDataURL: () => '',
    toBlob: noop,
  });

  const sandbox = {
    window: {},
    document: {
      createElement: elementStub,
      createElementNS: elementStub,
      addEventListener: noop,
      removeEventListener: noop,
      querySelector: noop,
      documentElement: {
        clientWidth: 1920,
        clientHeight: 1080,
      },
      body: {
        appendChild: noop,
        removeChild: noop,
      },
      cookie: '',
    },
    navigator: {
      userAgent,
      appCodeName: 'Mozilla',
      appName: 'Netscape',
      platform: 'Win32',
      language: 'en-US',
      languages: ['en-US'],
      hardwareConcurrency: 8,
      deviceMemory: 8,
      maxTouchPoints: 0,
    },
    location: {
      href: 'https://www.tiktok.com/',
    },
    crypto: {
      getRandomValues: (buffer) => crypto.randomFillSync(buffer),
      subtle: crypto.webcrypto ? crypto.webcrypto.subtle : undefined,
    },
    performance: {
      now: () => Date.now(),
      timeOrigin: Date.now(),
      getEntriesByType: () => [],
    },
    setTimeout,
    clearTimeout,
    setInterval,
    clearInterval,
    URL,
    atob: (str) => Buffer.from(str, 'base64').toString('binary'),
    btoa: (str) => Buffer.from(str, 'binary').toString('base64'),
    console,
  };

  sandbox.window = sandbox;
  sandbox.self = sandbox.window;
  sandbox.globalThis = sandbox.window;
  sandbox.location.href = urlToSign;

  return sandbox;
}

async function main() {
  const urlToSign = process.argv[2];
  const userAgent = process.argv[3] || DEFAULT_USER_AGENT;

  if (!urlToSign) {
    console.error('Uso: node tiktok_signer.js "<url>" "<userAgent>"');
    process.exit(1);
  }

  const script = await ensureAcrawlerScript();
  const sandbox = createSandbox(urlToSign, userAgent);

  try {
    vm.createContext(sandbox);
    vm.runInContext(script, sandbox, {
      filename: 'acrawler.js',
      timeout: 5000,
    });
  } catch (error) {
    console.error('Erro ao inicializar acrawler:', error);
    process.exit(2);
  }

  const signer = sandbox.window?.byted_acrawler?.sign;
  if (typeof signer !== 'function') {
    console.error('Função window.byted_acrawler.sign não encontrada');
    process.exit(3);
  }

  let result;
  try {
    result = signer({ url: urlToSign, ua: userAgent });
  } catch (error) {
    console.error('Erro ao gerar assinatura:', error);
    process.exit(4);
  }

  if (typeof result === 'string') {
    process.stdout.write(result);
  } else if (result && typeof result === 'object') {
    // Alguns builds retornam objeto { X-Bogus: '...' }
    const value = result['X-Bogus'] || result['x-bogus'] || result.value;
    if (!value) {
      process.stdout.write(JSON.stringify(result));
    } else {
      process.stdout.write(value);
    }
  } else {
    process.stdout.write(String(result));
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(5);
});
