import { useMemo, useState } from 'react';
import { Cookie, AlertCircle, CheckCircle, Info, Shuffle } from 'lucide-react';
import Modal from '@/components/common/Modal';
import Button from '@/components/common/Button';

const NUMBER_REGEX = /^-?\d+(\.\d+)?$/;

export default function CookiesImportModal({ isOpen, onClose, onImport, account, isLoading }) {
  const [mode, setMode] = useState('unified'); // unified | advanced
  const isAdvanced = mode === 'advanced';

  const [cookiesText, setCookiesText] = useState('');
  const [error, setError] = useState(null);
  const [validationStatus, setValidationStatus] = useState(null);
  const [parsedPayload, setParsedPayload] = useState(null);

  // advanced mode state
  const [advancedCookies, setAdvancedCookies] = useState('');
  const [advancedLocalStorage, setAdvancedLocalStorage] = useState('');
  const [advancedSessionStorage, setAdvancedSessionStorage] = useState('');
  const [advancedPreview, setAdvancedPreview] = useState(null);

  const advancedInstructionText = useMemo(
    () =>
      `Cole o dump no formato "chave[TAB]valor" exportado do DevTools. Exemplo:
ttwid\t7568993396133594631
webapp_showed_profile_tip\t1
web_dm_storage_...\t{}
sessionId\t{"sessionId":"...","timestamp":1762387716247}`,
    []
  );

  const resetState = () => {
    setCookiesText('');
    setError(null);
    setValidationStatus(null);
    setParsedPayload(null);
    setAdvancedCookies('');
    setAdvancedLocalStorage('');
    setAdvancedSessionStorage('');
    setAdvancedPreview(null);
  };

  const handleModeChange = (nextMode) => {
    if (nextMode === mode) return;
    setMode(nextMode);
    setError(null);
    setValidationStatus(null);
    setParsedPayload(null);
    setAdvancedPreview(null);
  };

  const handleUnifiedChange = (e) => {
    setCookiesText(e.target.value);
    setError(null);
    setValidationStatus(null);
    setParsedPayload(null);
  };

  const parseCookiesInput = (text) => {
    const trimmed = text.trim();
    if (!trimmed) {
      throw new Error('Informe os cookies exportados.');
    }

    let parsed;
    try {
      parsed = JSON.parse(trimmed);
    } catch (err) {
      throw new Error('Formato inválido: forneça JSON válido para os cookies.');
    }

    if (Array.isArray(parsed)) {
      return parsed;
    }
    if (parsed.cookies && Array.isArray(parsed.cookies)) {
      return parsed.cookies;
    }
    throw new Error('Formato inválido: deve ser um array de cookies ou objeto com chave "cookies".');
  };

  const coerceValue = (value) => {
    const trimmed = value.trim();
    if (!trimmed) {
      return '';
    }

    if (
      (trimmed.startsWith('{') && trimmed.endsWith('}')) ||
      (trimmed.startsWith('[') && trimmed.endsWith(']'))
    ) {
      try {
        return JSON.parse(trimmed);
      } catch (err) {
        return trimmed;
      }
    }

    if (trimmed === 'true') return true;
    if (trimmed === 'false') return false;
    if (NUMBER_REGEX.test(trimmed)) {
      return trimmed.includes('.') ? parseFloat(trimmed) : parseInt(trimmed, 10);
    }
    return trimmed;
  };

  const parseStorageDump = (text) => {
    const result = {};
    if (!text.trim()) {
      return result;
    }

    const lines = text.split(/\r?\n/);
    for (const line of lines) {
      if (!line.trim()) continue;
      const parts = line.split(/\t+/);
      const key = (parts.shift() || '').trim();
      if (!key) continue;
      const rawValue = parts.join('\t');
      result[key] = coerceValue(rawValue);
    }
    return result;
  };

  const validateUnifiedPayload = () => {
    try {
      const parsed = JSON.parse(cookiesText.trim());

      let payload;
      let cookiesList = null;
      if (Array.isArray(parsed)) {
        cookiesList = parsed;
        payload = { cookies: parsed };
      } else if (parsed.cookies && Array.isArray(parsed.cookies)) {
        cookiesList = parsed.cookies;
        payload = parsed;
      } else {
        throw new Error('Formato inválido: deve ser um array de cookies ou objeto com chave "cookies".');
      }

      if (cookiesList.length === 0) {
        throw new Error('Lista de cookies está vazia');
      }

      for (let i = 0; i < cookiesList.length; i++) {
        const cookie = cookiesList[i];
        if (!cookie.name || !cookie.value) {
          throw new Error(`Cookie na posição ${i} não possui "name" ou "value".`);
        }
      }

      setValidationStatus({ success: true, count: cookiesList.length });
      setParsedPayload(payload);
      return payload;
    } catch (err) {
      setError(err.message);
      setValidationStatus(null);
      setParsedPayload(null);
      return null;
    }
  };

  const buildAdvancedPayload = () => {
    if (!advancedCookies.trim()) {
      throw new Error('Informe os cookies exportados.');
    }

    const cookiesList = parseCookiesInput(advancedCookies);
    const localPayload = parseStorageDump(advancedLocalStorage);
    const sessionPayload = parseStorageDump(advancedSessionStorage);

    const payload = { cookies: cookiesList };
    if (Object.keys(localPayload).length > 0) {
      payload.local_storage = localPayload;
    }
    if (Object.keys(sessionPayload).length > 0) {
      payload.session_storage = sessionPayload;
    }

    setValidationStatus({ success: true, count: cookiesList.length });
    setError(null);
    return payload;
  };

  const handleImport = async () => {
    try {
      let payload = null;
      if (isAdvanced) {
        payload = buildAdvancedPayload();
        setAdvancedPreview(JSON.stringify(payload, null, 2));
      } else {
        payload = validateUnifiedPayload();
      }

      if (!payload) {
        return;
      }

      await onImport(payload);
      resetState();
    } catch (err) {
      const message =
        err?.response?.data?.message ||
        err?.message ||
        'Erro ao importar cookies.';
      setError(message);
    }
  };

  const handleClose = () => {
    resetState();
    onClose();
  };

  const canImport = isAdvanced
    ? advancedCookies.trim().length > 0
    : cookiesText.trim().length > 0;

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={`Atualizar Cookies - ${account?.account_name || ''}`}
      size="lg"
      footer={
        <>
          <Button variant="ghost" onClick={handleClose}>
            Cancelar
          </Button>
          <Button
            variant="primary"
            icon={Cookie}
            onClick={handleImport}
            loading={isLoading}
            disabled={!canImport || isLoading}
          >
            Importar Cookies
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div className="flex gap-2">
          <Button
            variant={mode === 'unified' ? 'primary' : 'secondary'}
            size="sm"
            onClick={() => handleModeChange('unified')}
          >
            JSON unificado
          </Button>
          <Button
            variant={isAdvanced ? 'primary' : 'secondary'}
            size="sm"
            icon={Shuffle}
            onClick={() => handleModeChange('advanced')}
          >
            Converter dumps (local/session)
          </Button>
        </div>

        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-text-secondary space-y-2">
              {isAdvanced ? (
                <>
                  <p className="font-medium text-text-primary">Modo conversor de dumps:</p>
                  <ul className="list-disc list-inside space-y-1 ml-2">
                    <li>Exporte os <strong>cookies</strong> com a extensão (JSON).</li>
                    <li>Copie os dumps de <strong>localStorage</strong> e <strong>sessionStorage</strong> do DevTools (aba Aplicativo).</li>
                    <li>Cole cada dump no campo correspondente. Cada linha deve ser <code>chave[TAB]valor</code>.</li>
                    <li>O conversor detecta JSON, números e booleanos automaticamente.</li>
                  </ul>
                </>
              ) : (
                <>
                  <p className="font-medium text-text-primary">Como exportar cookies do TikTok:</p>
                  <ol className="list-decimal list-inside space-y-1 ml-2">
                    <li>Instale a extensão <strong>Cookie-Editor</strong> ou <strong>EditThisCookie</strong>.</li>
                    <li>Acesse <a href="https://www.tiktok.com" target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">tiktok.com</a> e faça login.</li>
                    <li>Clique no ícone da extensão e selecione “Export” ou “Export All”.</li>
                    <li>Cole o JSON exportado no campo abaixo.</li>
                  </ol>
                  <p className="text-xs text-text-tertiary mt-2">
                    💡 Os cookies devem ser do domínio <code className="bg-black/20 px-1 rounded">.tiktok.com</code>.
                  </p>
                </>
              )}
            </div>
          </div>
        </div>

        {isAdvanced ? (
          <>
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                Cookies (JSON exportado):
              </label>
              <textarea
                value={advancedCookies}
                onChange={(e) => {
                  setAdvancedCookies(e.target.value);
                  setAdvancedPreview(null);
                  setValidationStatus(null);
                  setError(null);
                }}
                placeholder='[{"name": "sessionid", "value": "...", "domain": ".tiktok.com"}, ...]'
                className="w-full h-48 px-4 py-3 bg-background-elevated border border-border rounded-lg text-text-primary placeholder-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent font-mono text-sm resize-none"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                Dump de localStorage:
              </label>
              <textarea
                value={advancedLocalStorage}
                onChange={(e) => {
                  setAdvancedLocalStorage(e.target.value);
                  setAdvancedPreview(null);
                  setError(null);
                }}
                placeholder={advancedInstructionText}
                className="w-full h-36 px-4 py-3 bg-background-elevated border border-border rounded-lg text-text-primary placeholder-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent font-mono text-sm resize-none"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                Dump de sessionStorage:
              </label>
              <textarea
                value={advancedSessionStorage}
                onChange={(e) => {
                  setAdvancedSessionStorage(e.target.value);
                  setAdvancedPreview(null);
                  setError(null);
                }}
                placeholder={advancedInstructionText}
                className="w-full h-36 px-4 py-3 bg-background-elevated border border-border rounded-lg text-text-primary placeholder-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent focus;border-transparent font-mono text-sm resize-none"
              />
            </div>

            <Button
              variant="secondary"
              size="sm"
              className="w-full"
              onClick={() => {
                try {
                  const payload = buildAdvancedPayload();
                  setAdvancedPreview(JSON.stringify(payload, null, 2));
                  setError(null);
                } catch (err) {
                  setAdvancedPreview(null);
                  setError(err.message || 'Falha ao converter dump.');
                }
              }}
            >
              Gerar pré-visualização
            </Button>

            {advancedPreview && (
              <div className="bg-black/30 border border-border rounded-lg p-3">
                <p className="text-xs text-text-tertiary mb-2">
                  Pré-visualização do JSON que será enviado ao backend:
                </p>
                <pre className="text-xs text-text-primary whitespace-pre-wrap overflow-auto max-h-48">
                  {advancedPreview}
                </pre>
              </div>
            )}
          </>
        ) : (
          <>
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                Cole o JSON dos cookies aqui:
              </label>
              <textarea
                value={cookiesText}
                onChange={handleUnifiedChange}
                placeholder='[{"name": "sessionid", "value": "...", "domain": ".tiktok.com"}, ...]'
                className="w-full h-64 px-4 py-3 bg-background-elevated border border-border rounded-lg text-text-primary placeholder-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent font-mono text-sm resize-none"
              />
            </div>

            {validationStatus && (
              <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3">
                <div className="flex items-center gap-2 text-green-400">
                  <CheckCircle className="w-4 h-4" />
                  <span className="text-sm font-medium">
                    {validationStatus.count} cookies válidos encontrados
                  </span>
                </div>
              </div>
            )}

            {cookiesText.trim() && !validationStatus && !error && (
              <Button
                variant="secondary"
                size="sm"
                onClick={validateUnifiedPayload}
                className="w-full"
              >
                Validar Formato
              </Button>
            )}
          </>
        )}

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
            <div className="flex items-start gap-2 text-red-400">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium">Erro de validação:</p>
                <p className="text-red-300/80 mt-1 whitespace-pre-wrap">{error}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
