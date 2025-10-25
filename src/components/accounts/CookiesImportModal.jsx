import { useState } from 'react';
import { Cookie, AlertCircle, CheckCircle, Info } from 'lucide-react';
import Modal from '@/components/common/Modal';
import Button from '@/components/common/Button';

export default function CookiesImportModal({ isOpen, onClose, onImport, account, isLoading }) {
  const [cookiesText, setCookiesText] = useState('');
  const [error, setError] = useState(null);
  const [validationStatus, setValidationStatus] = useState(null);

  const handleTextChange = (e) => {
    setCookiesText(e.target.value);
    setError(null);
    setValidationStatus(null);
  };

  const validateCookies = () => {
    try {
      const parsed = JSON.parse(cookiesText.trim());

      let cookiesList = null;
      if (Array.isArray(parsed)) {
        cookiesList = parsed;
      } else if (parsed.cookies && Array.isArray(parsed.cookies)) {
        cookiesList = parsed.cookies;
      } else {
        throw new Error('Formato inválido: deve ser um array de cookies ou objeto com chave "cookies"');
      }

      if (cookiesList.length === 0) {
        throw new Error('Lista de cookies está vazia');
      }

      // Valida estrutura básica
      for (let i = 0; i < cookiesList.length; i++) {
        const cookie = cookiesList[i];
        if (!cookie.name || !cookie.value) {
          throw new Error(`Cookie na posição ${i} não possui 'name' ou 'value'`);
        }
      }

      setValidationStatus({
        success: true,
        count: cookiesList.length
      });
      return cookiesList;
    } catch (err) {
      setError(err.message);
      setValidationStatus(null);
      return null;
    }
  };

  const handleImport = async () => {
    const cookiesList = validateCookies();
    if (!cookiesList) return;

    try {
      await onImport(cookiesList);
      setCookiesText('');
      setError(null);
      setValidationStatus(null);
    } catch (err) {
      setError(err.response?.data?.message || 'Erro ao importar cookies');
    }
  };

  const handleClose = () => {
    setCookiesText('');
    setError(null);
    setValidationStatus(null);
    onClose();
  };

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
            disabled={!cookiesText.trim() || isLoading}
          >
            Importar Cookies
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {/* Instruções */}
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-text-secondary space-y-2">
              <p className="font-medium text-text-primary">Como exportar cookies do TikTok:</p>
              <ol className="list-decimal list-inside space-y-1 ml-2">
                <li>Instale a extensão <strong>Cookie-Editor</strong> ou <strong>EditThisCookie</strong> no seu navegador</li>
                <li>Acesse <a href="https://www.tiktok.com" target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">tiktok.com</a> e faça login normalmente</li>
                <li>Clique no ícone da extensão e selecione "Export" ou "Export All"</li>
                <li>Cole o JSON exportado no campo abaixo</li>
              </ol>
              <p className="text-xs text-text-tertiary mt-2">
                💡 Os cookies devem ser do domínio <code className="bg-black/20 px-1 rounded">.tiktok.com</code>
              </p>
            </div>
          </div>
        </div>

        {/* Campo de texto */}
        <div>
          <label className="block text-sm font-medium text-text-primary mb-2">
            Cole o JSON dos cookies aqui:
          </label>
          <textarea
            value={cookiesText}
            onChange={handleTextChange}
            placeholder='[{"name": "sessionid", "value": "...", "domain": ".tiktok.com"}, ...]'
            className="w-full h-64 px-4 py-3 bg-background-elevated border border-border rounded-lg text-text-primary placeholder-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent font-mono text-sm resize-none"
          />
        </div>

        {/* Status de validação */}
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

        {/* Erro */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
            <div className="flex items-start gap-2 text-red-400">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium">Erro de validação:</p>
                <p className="text-red-300/80 mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Botão de validação prévia */}
        {cookiesText.trim() && !validationStatus && !error && (
          <Button
            variant="secondary"
            size="sm"
            onClick={validateCookies}
            className="w-full"
          >
            Validar Formato
          </Button>
        )}
      </div>
    </Modal>
  );
}
