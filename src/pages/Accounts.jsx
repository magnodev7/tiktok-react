import { Plus, Users as UsersIcon, AlertCircle, Edit2, Trash2, Power, PowerOff, Cookie, ShieldCheck } from 'lucide-react';
import { useState } from 'react';
import Button from '@/components/common/Button';
import Card from '@/components/common/Card';
import Badge from '@/components/common/Badge';
import Modal from '@/components/common/Modal';
import Input from '@/components/common/Input';
import { useAccounts, useAddAccount, useUpdateAccount, useDeleteAccount, useActivateAccount, useDeactivateAccount, useUpdateCookies, useValidateCookies } from '@/hooks/useAccounts';
import Spinner from '@/components/common/Spinner';
import CookiesImportModal from '@/components/accounts/CookiesImportModal';
import { useToast } from '@/components/common/ToastContainer';

export default function Accounts() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentEditId, setCurrentEditId] = useState(null);
  const [loadingAccountId, setLoadingAccountId] = useState(null);
  const [validatingAccountId, setValidatingAccountId] = useState(null);
  const [isCookiesModalOpen, setIsCookiesModalOpen] = useState(false);
  const [selectedAccountForCookies, setSelectedAccountForCookies] = useState(null);
  const [newAccount, setNewAccount] = useState({
    username: '',
    password: '',
    cookies: '',
    description: ''
  });
  const [error, setError] = useState('');

  const toast = useToast();

  const { data: accounts, isLoading } = useAccounts();
  const addAccountMutation = useAddAccount();
  const updateAccountMutation = useUpdateAccount();
  const deleteAccountMutation = useDeleteAccount();
  const activateAccountMutation = useActivateAccount();
  const deactivateAccountMutation = useDeactivateAccount();
  const updateCookiesMutation = useUpdateCookies();
  const validateCookiesMutation = useValidateCookies();

  const getErrorMessage = (err, fallback = 'Ocorreu um erro.') => {
    if (!err) return fallback;
    const payload = err.response?.data;
    if (payload) {
      if (typeof payload === 'string') return payload;
      if (payload.message) return payload.message;
      if (Array.isArray(payload.detail)) {
        return payload.detail
          .map(item => item?.msg || item?.message || JSON.stringify(item))
          .join(' | ');
      }
      if (payload.detail) return payload.detail;
    }
    return err.message || fallback;
  };

  const handleAddAccount = async () => {
    setError('');

    // Validação
    if (!newAccount.username.trim()) {
      setError('Username é obrigatório');
      return;
    }

    // Validar formato (sem @, apenas letras, números, _ e -)
    const cleanUsername = newAccount.username.trim().replace(/^@/, '');
    if (!/^[a-zA-Z0-9_-]+$/.test(cleanUsername)) {
      setError('Username deve conter apenas letras, números, _ e - (sem @)');
      return;
    }

    const rawCookies = newAccount.cookies.trim();
    const isEditing = Boolean(currentEditId);
    const hasCookiesPayload = Boolean(rawCookies);

    // Para criação, cookies ou senha são obrigatórios
    if (!isEditing && !hasCookiesPayload && !newAccount.password.trim()) {
      setError('Você deve fornecer senha OU cookies');
      return;
    }

    try {
      // ✅ Preparar dados exatamente como backend espera
      const data = {
        display_name: newAccount.username.trim() || null,
        description: newAccount.description?.trim() || null,
      };

      // Para criação, incluir account_name
      if (!isEditing) {
        data.account_name = cleanUsername;
        data.is_default = false;
      }

      // Parse dos cookies (se fornecidos)
      if (hasCookiesPayload) {
        try {
          const parsedCookies = JSON.parse(rawCookies);

          // Se for array (formato Chrome DevTools), converter para dict
          if (Array.isArray(parsedCookies)) {
            const cookiesDict = {};
            parsedCookies.forEach(cookie => {
              if (cookie.name && cookie.value) {
                cookiesDict[cookie.name] = cookie.value;
              }
            });
            data.cookies_data = cookiesDict;
          } else {
            // Já é dict
            data.cookies_data = parsedCookies;
          }
        } catch (e) {
          setError('Cookies inválidos. Deve ser um JSON válido.');
          return;
        }
      }

      console.log('📤 Enviando para API:', isEditing ? 'UPDATE' : 'CREATE', data);

      const mutationResult = isEditing
        ? await updateAccountMutation.mutateAsync({ accountId: currentEditId, accountData: data })
        : await addAccountMutation.mutateAsync(data);

      const successMessage =
        mutationResult?.meta?.message ||
        (isEditing ? 'Conta atualizada com sucesso!' : 'Conta adicionada com sucesso!');
      toast.success(successMessage);

      // Sucesso - fechar modal e limpar
      setIsModalOpen(false);
      setCurrentEditId(null);
      setNewAccount({ username: '', password: '', cookies: '', description: '' });
      setError('');

      if (hasCookiesPayload) {
        try {
          const { meta } = await validateCookiesMutation.mutateAsync({
            accountName: cleanUsername,
            visible: false,
            testMode: false,
          });
          toast.success(meta?.message || 'Cookies validados com sucesso!');
        } catch (validationError) {
          toast.error(getErrorMessage(validationError, 'Falha ao validar cookies.'));
        }
      }
    } catch (error) {
      console.error('❌ Erro completo:', error);
      console.error('❌ Resposta do backend:', error.response?.data);

      let errorMessage = isEditing ? 'Erro ao atualizar conta' : 'Erro ao adicionar conta';

      if (error.response?.data) {
        const errorData = error.response.data;

        if (Array.isArray(errorData.detail)) {
          errorMessage = errorData.detail
            .map(err => {
              const field = err.loc ? err.loc.slice(1).join(' → ') : 'Campo';
              return `${field}: ${err.msg}`;
            })
            .join('\n');
        } else if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        } else if (errorData.message) {
          errorMessage = errorData.message;
        }
      }

      setError(errorMessage);
      toast.error(errorMessage);
    }
  };

  const editAccount = (account) => {
    setCurrentEditId(account.id);
    setNewAccount({
      username: account.account_name,
      password: '',
      cookies: account.cookies_data ? JSON.stringify(account.cookies_data, null, 2) : '',
      description: account.description || '',
    });
    setIsModalOpen(true);
  };

  const handleDeleteAccount = async (accountId, accountName) => {
    if (!window.confirm(`Tem certeza que deseja excluir a conta "${accountName}"?\n\nEsta ação não pode ser desfeita.`)) {
      return;
    }

    try {
      await deleteAccountMutation.mutateAsync(accountId);
    } catch (error) {
      console.error('Erro ao excluir conta:', error);
      const apiError = error.response?.data;
      const errorMsg = apiError?.message || apiError?.detail || 'Erro ao excluir conta';
      alert(errorMsg);
    }
  };

  const handleToggleActive = async (accountId, accountName, isActive) => {
    setLoadingAccountId(accountId);
    try {
      if (isActive) {
        await deactivateAccountMutation.mutateAsync(accountId);
      } else {
        await activateAccountMutation.mutateAsync(accountId);
      }
    } catch (error) {
      console.error('Erro ao alterar status da conta:', error);
      const apiError = error.response?.data;
      const errorMsg = apiError?.message || apiError?.detail || 'Erro ao alterar status da conta';
      alert(errorMsg);
    } finally {
      setLoadingAccountId(null);
    }
  };

  const handleValidateCookies = async (account) => {
    if (!account?.account_name) return;
    setValidatingAccountId(account.id);
    try {
      const { meta } = await validateCookiesMutation.mutateAsync({
        accountName: account.account_name,
        visible: false,
        testMode: false,
      });
      toast.success(meta?.message || 'Cookies validados com sucesso!');
    } catch (error) {
      console.error('Erro ao validar cookies:', error);
      toast.error(getErrorMessage(error, 'Falha ao validar cookies.'));
    } finally {
      setValidatingAccountId(null);
    }
  };

  const handleOpenCookiesModal = (account) => {
    setSelectedAccountForCookies(account);
    setIsCookiesModalOpen(true);
  };

  const handleCloseCookiesModal = () => {
    setIsCookiesModalOpen(false);
    setSelectedAccountForCookies(null);
  };

  const handleImportCookies = async (payload) => {
    if (!selectedAccountForCookies) return;
    const normalizedPayload = Array.isArray(payload)
      ? { cookies: payload }
      : payload;

    try {
      await updateCookiesMutation.mutateAsync({
        accountId: selectedAccountForCookies.id,
        payload: normalizedPayload,
      });
      toast.success(`Cookies atualizados com sucesso para '${selectedAccountForCookies.account_name}'`);

      try {
        setValidatingAccountId(selectedAccountForCookies.id);
        const { meta } = await validateCookiesMutation.mutateAsync({
          accountName: selectedAccountForCookies.account_name,
          visible: false,
          testMode: false,
        });
        toast.success(meta?.message || 'Cookies validados com sucesso!');
      } catch (validationError) {
        console.error('Erro ao validar cookies após atualização:', validationError);
        if (validationError?.response?.status === 405) {
          toast.info('Cookies salvos, mas o endpoint de validação não está disponível no backend.');
        } else {
          toast.error(getErrorMessage(validationError, 'Falha ao validar cookies.'));
        }
      } finally {
        setValidatingAccountId(null);
      }

      handleCloseCookiesModal();
    } catch (error) {
      console.error('Erro ao atualizar cookies:', error);
      toast.error(getErrorMessage(error, 'Erro ao atualizar cookies.'));
      throw error; // Re-throw para o modal mostrar o erro
    }
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setCurrentEditId(null);
    setError('');
    setNewAccount({ username: '', password: '', cookies: '', description: '' });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary mb-2">Contas TikTok</h1>
          <p className="text-text-secondary">Gerencie suas contas conectadas</p>
        </div>
        <Button icon={Plus} onClick={() => setIsModalOpen(true)}>
          Adicionar Conta
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-accent-subtle rounded-lg">
              <UsersIcon className="w-5 h-5 text-accent" />
            </div>
            <div>
              <p className="text-sm text-text-secondary">Total de Contas</p>
              <p className="text-2xl font-bold text-text-primary">{accounts?.length || 0}</p>
            </div>
          </div>
        </Card>
        <Card>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-500/10 rounded-lg">
              <UsersIcon className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <p className="text-sm text-text-secondary">Ativas</p>
              <p className="text-2xl font-bold text-text-primary">
                {accounts?.filter(a => a.is_active).length || 0}
              </p>
            </div>
          </div>
        </Card>
        <Card>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <UsersIcon className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <p className="text-sm text-text-secondary">Vídeos Agendados</p>
              <p className="text-2xl font-bold text-text-primary">
                {accounts?.reduce((sum, acc) => sum + (acc.total_uploads || 0), 0) || 0}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Accounts Grid */}
      {accounts && accounts.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {accounts.map((account) => (
            <Card
              key={account.id}
              variant="interactive"
              data-testid="account-card"
              data-account-name={account.account_name}
            >
              {/* Header do Card */}
              <div className="flex items-start gap-3 mb-4">
                <div className="w-12 h-12 rounded-full overflow-hidden flex items-center justify-center flex-shrink-0 bg-accent/10 border border-border">
                  {account.profile_pic ? (
                    <img
                      src={account.profile_pic}
                      alt={account.display_name || account.account_name}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  ) : (
                    <span className="text-accent font-bold text-lg">
                      {account.account_name?.charAt(0).toUpperCase()}
                    </span>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-text-primary truncate">
                    @{account.account_name}
                  </h3>
                  {account.display_name && account.display_name !== account.account_name && (
                    <p className="text-sm text-text-secondary truncate">{account.display_name}</p>
                  )}
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Badge variant={account.is_active ? 'success' : 'error'} dot>
                      {account.is_active ? 'Ativa' : 'Inativa'}
                    </Badge>
                    {account.is_default && (
                      <Badge variant="info">
                        Padrão
                      </Badge>
                    )}
                    {/* Alerta de cookies ausentes/inválidos */}
                    {!account.cookies_data && account.is_active && (
                      <Badge variant="warning">
                        ⚠️ Sem cookies
                      </Badge>
                    )}
                  </div>
                </div>
              </div>

              {/* Alerta de cookies ausentes */}
              {!account.cookies_data && account.is_active && (
                <div className="mb-4 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
                  <p className="text-sm text-yellow-500 font-medium mb-1">
                    ⚠️ Cookies não configurados
                  </p>
                  <p className="text-xs text-text-secondary">
                    Esta conta não poderá postar vídeos automaticamente. Clique em "Editar" e adicione os cookies.
                  </p>
                </div>
              )}

              {/* Descrição */}
              {account.description && (
                <p className="text-sm text-text-secondary mb-4 line-clamp-2">
                  {account.description}
                </p>
              )}

              {/* Estatísticas */}
              <div className="border-t border-border pt-4 mb-4">
                <div className="grid grid-cols-2 gap-4 text-center">
                  <div>
                    <p className="text-sm text-text-secondary">Agendados</p>
                    <p className="text-lg font-semibold text-text-primary">
                      {account.scheduled_count || 0}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-text-secondary">Horários</p>
                    <p className="text-lg font-semibold text-text-primary">
                      {account.schedules_count || 0}
                    </p>
                  </div>
                </div>
              </div>

              {/* Ações */}
              <div className="flex flex-col gap-2">
                {/* Botão Ativar/Desativar */}
                <Button
                  variant={account.is_active ? 'destructive' : 'success'}
                  size="sm"
                  icon={account.is_active ? PowerOff : Power}
                  onClick={() => handleToggleActive(account.id, account.account_name, account.is_active)}
                  loading={loadingAccountId === account.id}
                  disabled={loadingAccountId !== null && loadingAccountId !== account.id}
                  className="w-full"
                >
                  {account.is_active ? 'Desativar' : 'Ativar'}
                </Button>

                {/* Botão Atualizar Cookies */}
                <Button
                  variant="secondary"
                  size="sm"
                  icon={Cookie}
                  onClick={() => handleOpenCookiesModal(account)}
                  className="w-full"
                >
                  Atualizar Cookies
                </Button>

                <Button
                  variant="secondary"
                  size="sm"
                  icon={ShieldCheck}
                  onClick={() => handleValidateCookies(account)}
                  loading={validatingAccountId === account.id && validateCookiesMutation.isPending}
                  disabled={
                    !account.cookies_data ||
                    (validatingAccountId !== null && validatingAccountId !== account.id)
                  }
                  className="w-full"
                >
                  Validar Cookies
                </Button>

                {/* Botões Editar e Excluir */}
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    icon={Edit2}
                    onClick={() => editAccount(account)}
                    className="flex-1"
                  >
                    Editar
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    icon={Trash2}
                    onClick={() => handleDeleteAccount(account.id, account.account_name)}
                    className="flex-1"
                  >
                    Excluir
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="text-center py-12">
          <UsersIcon className="w-16 h-16 text-text-tertiary mx-auto mb-4" />
          <h3 className="text-lg font-medium text-text-primary mb-2">
            Nenhuma conta conectada
          </h3>
          <p className="text-text-secondary mb-6">
            Adicione sua primeira conta TikTok para começar
          </p>
          <Button icon={Plus} onClick={() => setIsModalOpen(true)}>
            Conectar Conta
          </Button>
        </Card>
      )}

      {/* Add Account Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={closeModal}
        title={currentEditId ? "Editar Conta TikTok" : "Adicionar Conta TikTok"}
        footer={
          <>
            <Button variant="ghost" onClick={closeModal}>
              Cancelar
            </Button>
            <Button
              onClick={handleAddAccount}
              loading={currentEditId ? updateAccountMutation.isPending : addAccountMutation.isPending}
            >
              {currentEditId ? "Salvar Alterações" : "Conectar Conta"}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {/* Erro */}
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm text-red-400 whitespace-pre-wrap">{error}</p>
              </div>
            </div>
          )}

          {/* Username */}
          <Input
            label="Username"
            placeholder="novadigitalbra (sem @)"
            value={newAccount.username}
            onChange={(value) => setNewAccount({ ...newAccount, username: value })}
            helperText="Use apenas letras, números, _ e - (sem @)"
            disabled={!!currentEditId}
            required
          />

          {/* Descrição */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              Descrição (opcional)
            </label>
            <textarea
              placeholder="Descrição da conta..."
              value={newAccount.description}
              onChange={(e) => setNewAccount({ ...newAccount, description: e.target.value })}
              rows={2}
              className="w-full px-4 py-2 bg-background border border-border rounded-lg text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent text-sm resize-none"
            />
          </div>

          {/* Opção 1: Cookies (Recomendado) */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              🍪 Cookies do TikTok (Recomendado)
            </label>
            <textarea
              placeholder='Cole aqui os cookies em formato JSON: {"sessionid": "...", "tt_webid": "...", ...}'
              value={newAccount.cookies}
              onChange={(e) => setNewAccount({ ...newAccount, cookies: e.target.value })}
              rows={6}
              className="w-full px-4 py-2 bg-background border border-border rounded-lg text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent text-sm font-mono resize-none"
            />
            <p className="text-xs text-text-tertiary mt-1">
              Para obter os cookies: Faça login no TikTok, abra DevTools (F12), vá em Application → Cookies
            </p>
          </div>

          {/* Divisor */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-background-elevated text-text-tertiary">OU</span>
            </div>
          </div>

          {/* Opção 2: Senha (Login via Selenium) */}
          <Input
            type="password"
            label="Senha (Login Automático)"
            placeholder="••••••••"
            value={newAccount.password}
            onChange={(value) => setNewAccount({ ...newAccount, password: value })}
            helperText="Usaremos Selenium para fazer login automaticamente (não recomendado)"
          />

          {/* Aviso */}
          <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
            <p className="text-sm text-blue-400">
              ⚠️ <strong>Cookies são mais seguros e rápidos!</strong> Login via senha pode ser bloqueado pelo TikTok (captcha, 2FA).
            </p>
          </div>
        </div>
      </Modal>

      {/* Modal de Importação de Cookies */}
      <CookiesImportModal
        isOpen={isCookiesModalOpen}
        onClose={handleCloseCookiesModal}
        onImport={handleImportCookies}
        account={selectedAccountForCookies}
        isLoading={updateCookiesMutation.isPending}
      />
    </div>
  );
}
