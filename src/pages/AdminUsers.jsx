import { useState, useEffect } from 'react';
import Card from '@/components/common/Card';
import Button from '@/components/common/Button';
import Input from '@/components/common/Input';
import Spinner from '@/components/common/Spinner';
import { showError } from '@/utils/errorHandler';
import { useAuth } from '@/contexts/AuthContext';

import apiClient from '@/api/client';
const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8082').replace(/\/$/, '');

function authHeaders() {
  const token = localStorage.getItem('auth_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}


async function safeFetch(url, options = {}) {
  try {
    const method = options.method || 'get';
    const config = {
      url,
      method,
      headers: options.headers,
      data: options.body ? JSON.parse(options.body) : undefined,
    };
    const response = await apiClient(config);
    return response.data;
  } catch (error) {
    let detail = error.response?.data?.detail || error.response?.data?.message || error.message;
    throw new Error(`${error.response?.status || ''} ${error.response?.statusText || ''}${detail ? ' — ' + detail : ''}`);
  }
}

export default function AdminUsers() {
  const { user } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ username: '', email: '', fullName: '', password: '', isAdmin: false });
  const [formLoading, setFormLoading] = useState(false);
  const [alert, setAlert] = useState(null);

  useEffect(() => {
    if (user?.is_admin) {
      loadUsers();
    }
  }, [user]);

  async function loadUsers() {
    setLoading(true);
    try {
  const data = await safeFetch(`${API_URL}/auth/users`, { headers: authHeaders() });
      setUsers(data || []);
    } catch (error) {
      setAlert({ type: 'error', message: error.message });
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateUser(e) {
    e.preventDefault();
    if (!form.username || !form.password) {
      setAlert({ type: 'error', message: 'Preencha usuário e senha.' });
      return;
    }
    if (form.password.length < 6) {
      setAlert({ type: 'error', message: 'Senha deve ter pelo menos 6 caracteres.' });
      return;
    }
    setFormLoading(true);
    try {
      await safeFetch(`${API_URL}/auth/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({
          username: form.username,
          password: form.password,
          email: form.email || null,
          full_name: form.fullName || null,
          is_admin: form.isAdmin,
        }),
      });
      setAlert({ type: 'success', message: `Usuário "${form.username}" criado!` });
      setForm({ username: '', email: '', fullName: '', password: '', isAdmin: false });
      loadUsers();
    } catch (error) {
      setAlert({ type: 'error', message: error.message });
    } finally {
      setFormLoading(false);
    }
  }

  async function handleResetPassword(username) {
    const newPassword = prompt(`Digite a nova senha para ${username} (mínimo 6 caracteres):`);
    if (!newPassword || newPassword.length < 6) {
      setAlert({ type: 'error', message: 'Senha deve ter pelo menos 6 caracteres.' });
      return;
    }
    if (!window.confirm(`Confirma reset de senha para "${username}"? Nova senha: ${newPassword}`)) return;
    try {
      await safeFetch(`${API_URL}/auth/users/${encodeURIComponent(username)}/password`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ new_password: newPassword }),
      });
      setAlert({ type: 'success', message: `Senha resetada para ${username}.` });
    } catch (error) {
      setAlert({ type: 'error', message: error.message });
    }
  }

  async function handleDeleteUser(username) {
    if (!window.confirm(`Remover usuário "${username}"? Esta ação não pode ser desfeita.`)) return;
    try {
      await safeFetch(`${API_URL}/auth/users/${encodeURIComponent(username)}`, {
        method: 'DELETE',
        headers: authHeaders(),
      });
      setAlert({ type: 'success', message: `Usuário "${username}" removido!` });
      loadUsers();
    } catch (error) {
      setAlert({ type: 'error', message: error.message });
    }
  }

  async function handleChangeQuota(username, currentQuota) {
    const newQuota = prompt(`Alterar quota para ${username} (atual: ${currentQuota === -1 ? 'Ilimitada' : currentQuota}):\nDigite nova quota (número >= 1 ou -1 para ilimitado):`, currentQuota);
    if (newQuota === null) return;
    const quotaInt = parseInt(newQuota);
    if (isNaN(quotaInt) || (quotaInt !== -1 && quotaInt < 1)) {
      setAlert({ type: 'error', message: 'Quota inválida. Use 1, 2, 4 ou -1.' });
      return;
    }
    try {
      await safeFetch(`${API_URL}/auth/users/${encodeURIComponent(username)}/quota`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ account_quota: quotaInt })
      });
      setAlert({ type: 'success', message: `Quota de ${username} alterada para ${quotaInt === -1 ? 'Ilimitada' : quotaInt}` });
      loadUsers();
    } catch (error) {
      setAlert({ type: 'error', message: error.message });
    }
  }

  return (
    <Card>
      <h2 className="text-xl font-bold mb-4">Administração de Usuários</h2>
      {alert && (
        <div
          className={`mb-4 p-3 rounded-lg ${alert.type === 'error' ? 'bg-red-500/10 text-red-500' : 'bg-green-500/10 text-green-500'}`}
          data-testid="admin-user-alert"
        >
          {alert.message}
        </div>
      )}
      <form onSubmit={handleCreateUser} className="space-y-4 mb-8" data-testid="admin-user-form">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Input label="Usuário *" value={form.username} onChange={v => setForm(f => ({ ...f, username: v }))} required />
          <Input label="Email" value={form.email} onChange={v => setForm(f => ({ ...f, email: v }))} type="email" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Input label="Nome Completo" value={form.fullName} onChange={v => setForm(f => ({ ...f, fullName: v }))} />
          <Input label="Senha *" value={form.password} onChange={v => setForm(f => ({ ...f, password: v }))} type="password" required />
        </div>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={form.isAdmin} onChange={e => setForm(f => ({ ...f, isAdmin: e.target.checked }))} /> Administrador
        </label>
        <div className="flex gap-3">
          <Button type="submit" loading={formLoading} data-testid="admin-create-button">Criar Usuário</Button>
          <Button type="reset" variant="ghost" onClick={() => setForm({ username: '', email: '', fullName: '', password: '', isAdmin: false })}>Limpar</Button>
        </div>
      </form>
      <h3 className="text-lg font-semibold mb-4">Usuários Cadastrados</h3>
      {loading ? (
        <Spinner size="lg" />
      ) : users.length === 0 ? (
        <div className="text-center text-text-tertiary py-8">Nenhum usuário encontrado.</div>
      ) : (
        <div className="space-y-4">
          {users.map(u => (
            <Card
              key={u.username}
              className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 p-4"
              data-testid="admin-user-card"
              data-username={u.username}
            >
              <div>
                <div className="font-bold">{u.username}</div>
                <div className="text-sm text-text-secondary">{u.full_name || 'Sem nome'} • {u.email || 'Sem email'} • Quota: {u.account_quota === -1 ? 'Ilimitada' : u.account_quota}</div>
                <div className="flex gap-2 mt-2">
                  {u.is_admin && <span className="badge bg-green-500/10 text-green-500">Admin</span>}
                  <span className={`badge ${u.is_active ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}`}>{u.is_active ? 'Ativo' : 'Inativo'}</span>
                </div>
              </div>
              <div className="flex gap-2 flex-wrap mt-2 md:mt-0">
                <Button size="sm" onClick={() => handleResetPassword(u.username)}>Reset Senha</Button>
                <Button size="sm" onClick={() => handleChangeQuota(u.username, u.account_quota)}>Alterar Quota</Button>
                {(!u.is_admin || users.filter(x => x.is_admin).length > 1) && (
                  <Button size="sm" variant="danger" onClick={() => handleDeleteUser(u.username)}>
                    Remover
                  </Button>
                )}
                {u.is_admin && users.filter(x => x.is_admin).length === 1 && (
                  <span className="badge">Último Admin</span>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </Card>
  );
}
