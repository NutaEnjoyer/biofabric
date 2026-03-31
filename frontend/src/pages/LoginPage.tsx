import { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export function LoginPage() {
  const { login } = useAuth();
  const navigate   = useNavigate();
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [error, setError]       = useState('');
  const [loading, setLoading]   = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/', { replace: true });
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      setError(detail || 'Неверный email или пароль');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-sm border border-[#E2E8F0] w-full max-w-sm p-8">
        {/* Logo */}
        <div className="mb-8 text-center">
          <span className="text-2xl font-bold text-[#2563EB]">BioFabric</span>
          <span className="ml-2 text-sm text-[#64748B]">ERP</span>
          <p className="mt-2 text-sm text-[#64748B]">Войдите в систему</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[#1E293B] mb-1">
              Email
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@biofabric.ru"
              className="w-full px-3 py-2.5 rounded-lg border border-[#E2E8F0] text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB] focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#1E293B] mb-1">
              Пароль
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-3 py-2.5 rounded-lg border border-[#E2E8F0] text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB] focus:border-transparent"
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-[#2563EB] text-white text-sm font-medium rounded-lg hover:bg-[#1D4ED8] disabled:opacity-50 transition-colors"
          >
            {loading ? 'Вход...' : 'Войти'}
          </button>
        </form>
      </div>
    </div>
  );
}
