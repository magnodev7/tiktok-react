import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Mail, Lock } from 'lucide-react';
import Input from '@/components/common/Input';
import Button from '@/components/common/Button';
import { useAuth } from '@/contexts/AuthContext';
import { showError } from '@/utils/errorHandler';
import logo from '@/assets/logo.png';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(username, password);
      navigate('/');
    } catch (error) {
      showError(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-background-subtle flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6">
        {/* Logo */}
        <div className="flex justify-center items-center px-4">
          <img
            src={logo}
            alt="Logo"
            className="w-full max-w-xs sm:max-w-sm md:max-w-md h-auto object-contain filter drop-shadow-2xl"
          />
        </div>

        {/* Login Form */}
        <div className="bg-background-elevated/50 backdrop-blur-xl border border-border rounded-2xl p-8 shadow-xl">
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              type="text"
              label="Usuário"
              placeholder="seu_usuario"
              icon={Mail}
              value={username}
              onChange={setUsername}
              required
            />

            <Input
              type="password"
              label="Senha"
              placeholder="••••••••"
              icon={Lock}
              value={password}
              onChange={setPassword}
              required
            />

            <div className="flex items-center justify-between text-sm">
              <label className="flex items-center gap-2 text-text-secondary cursor-pointer">
                <input type="checkbox" className="rounded border-border" />
                Lembrar-me
              </label>
              <Link to="/forgot-password" className="text-accent hover:underline">
                Esqueceu a senha?
              </Link>
            </div>

            <Button type="submit" fullWidth loading={loading}>
              Entrar
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-text-secondary">
              Não tem uma conta?{' '}
              <Link to="/register" className="text-accent hover:underline font-medium">
                Registre-se
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
