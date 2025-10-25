import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Mail, Lock, User } from 'lucide-react';
import Input from '@/components/common/Input';
import Button from '@/components/common/Button';
import { useAuth } from '@/contexts/AuthContext';
import { validateEmail, validatePassword } from '@/utils/validators';
import { showError } from '@/utils/errorHandler';

export default function Register() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrors({});

    // Validações
    const newErrors = {};
    
    if (!name.trim()) {
      newErrors.name = 'Nome é obrigatório';
    }

    if (!validateEmail(email)) {
      newErrors.email = 'Email inválido';
    }

    const passwordValidation = validatePassword(password);
    if (!passwordValidation.valid) {
      newErrors.password = passwordValidation.message;
    }

    if (password !== confirmPassword) {
      newErrors.confirmPassword = 'As senhas não coincidem';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setLoading(true);
    try {
      await register(name, email, password);
      navigate('/');
    } catch (error) {
      showError(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-background-subtle flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-accent rounded-2xl mb-4">
            <span className="text-3xl font-bold text-white">T</span>
          </div>
          <h1 className="text-2xl font-bold text-text-primary mb-2">Criar Conta</h1>
          <p className="text-text-secondary">Comece a agendar seus vídeos no TikTok</p>
        </div>

        {/* Register Form */}
        <div className="bg-background-elevated/50 backdrop-blur-xl border border-border rounded-2xl p-8 shadow-xl">
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              type="text"
              label="Nome Completo"
              placeholder="Seu nome"
              icon={User}
              value={name}
              onChange={setName}
              error={!!errors.name}
              helperText={errors.name}
              required
            />

            <Input
              type="email"
              label="Email"
              placeholder="seu@email.com"
              icon={Mail}
              value={email}
              onChange={setEmail}
              error={!!errors.email}
              helperText={errors.email}
              required
            />

            <Input
              type="password"
              label="Senha"
              placeholder="••••••••"
              icon={Lock}
              value={password}
              onChange={setPassword}
              error={!!errors.password}
              helperText={errors.password}
              required
            />

            <Input
              type="password"
              label="Confirmar Senha"
              placeholder="••••••••"
              icon={Lock}
              value={confirmPassword}
              onChange={setConfirmPassword}
              error={!!errors.confirmPassword}
              helperText={errors.confirmPassword}
              required
            />

            <div className="text-sm">
              <label className="flex items-start gap-2 text-text-secondary cursor-pointer">
                <input type="checkbox" className="mt-0.5 rounded border-border" required />
                <span>
                  Eu aceito os{' '}
                  <a href="#" className="text-accent hover:underline">
                    Termos de Uso
                  </a>{' '}
                  e{' '}
                  <a href="#" className="text-accent hover:underline">
                    Política de Privacidade
                  </a>
                </span>
              </label>
            </div>

            <Button type="submit" fullWidth loading={loading}>
              Criar Conta
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-text-secondary">
              Já tem uma conta?{' '}
              <Link to="/login" className="text-accent hover:underline font-medium">
                Fazer login
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
