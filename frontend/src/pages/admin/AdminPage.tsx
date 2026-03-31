import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/client';
import { Trash2, Pencil, Plus, X, Check, ShieldCheck } from 'lucide-react';

// ─── Типы ────────────────────────────────────────────────────────────────────

interface Role {
  role_id: number;
  role_code: string;
  name: string;
}

interface AppUser {
  user_id: number;
  full_name: string;
  email: string;
  username: string | null;
  roles: string[] | null;
  created_at: string;
}

// ─── Группировка ролей по модулям ────────────────────────────────────────────

const ROLE_GROUPS: { label: string; codes: string[] }[] = [
  { label: 'Системные',     codes: ['admin', 'editor', 'viewer'] },
  { label: 'Юридический',   codes: ['legal_admin', 'legal_user', 'legal_viewer'] },
  { label: 'ОКС',           codes: ['oks_admin', 'oks_responsible', 'oks_initiator', 'oks_viewer'] },
  { label: 'Маркетинг',     codes: ['author', 'reviewer', 'approver', 'publisher'] },
];

// ─── API ─────────────────────────────────────────────────────────────────────

const fetchUsers = () => api.get('/auth/admin/users').then(r => r.data as AppUser[]);
const fetchRoles = () => api.get('/auth/admin/roles').then(r => r.data as Role[]);

// ─── Компонент создания пользователя ─────────────────────────────────────────

function CreateUserModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({ full_name: '', email: '', password: '', username: '' });
  const [err, setErr] = useState('');

  const mut = useMutation({
    mutationFn: (data: typeof form) => api.post('/auth/admin/users', data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-users'] }); onClose(); },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setErr(msg || 'Ошибка создания');
    },
  });

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-semibold text-[#1E293B]">Новый пользователь</h3>
          <button onClick={onClose} className="text-[#94A3B8] hover:text-[#1E293B]">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-3">
          {(['full_name', 'email', 'username', 'password'] as const).map((field) => (
            <div key={field}>
              <label className="block text-xs font-medium text-[#64748B] mb-1">
                {{ full_name: 'ФИО', email: 'Email', username: 'Логин (опц.)', password: 'Пароль' }[field]}
              </label>
              <input
                type={field === 'password' ? 'password' : 'text'}
                required={field !== 'username'}
                value={form[field]}
                onChange={(e) => setForm(f => ({ ...f, [field]: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-[#E2E8F0] text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
              />
            </div>
          ))}
        </div>

        {err && <p className="mt-3 text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{err}</p>}

        <div className="flex gap-2 mt-5">
          <button
            onClick={() => mut.mutate(form)}
            disabled={mut.isPending}
            className="flex-1 py-2 bg-[#2563EB] text-white text-sm font-medium rounded-lg hover:bg-[#1D4ED8] disabled:opacity-50"
          >
            {mut.isPending ? 'Создание...' : 'Создать'}
          </button>
          <button onClick={onClose} className="px-4 py-2 border border-[#E2E8F0] rounded-lg text-sm text-[#64748B] hover:bg-gray-50">
            Отмена
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Панель редактирования ролей ──────────────────────────────────────────────

function RolesPanel({
  user,
  allRoles,
  onClose,
}: {
  user: AppUser;
  allRoles: Role[];
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const current = new Set(user.roles ?? []);
  const [selected, setSelected] = useState<Set<string>>(new Set(current));

  const roleMap = Object.fromEntries(allRoles.map(r => [r.role_code, r.name]));

  const mut = useMutation({
    mutationFn: (roles: string[]) =>
      api.put(`/auth/admin/users/${user.user_id}/roles`, { roles }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-users'] }); onClose(); },
  });

  const toggle = (code: string) => {
    setSelected(s => {
      const next = new Set(s);
      next.has(code) ? next.delete(code) : next.add(code);
      return next;
    });
  };

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="font-semibold text-[#1E293B]">Роли пользователя</h3>
            <p className="text-sm text-[#64748B]">{user.full_name}</p>
          </div>
          <button onClick={onClose} className="text-[#94A3B8] hover:text-[#1E293B]">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-5">
          {ROLE_GROUPS.map(group => {
            const groupRoles = group.codes.filter(c => roleMap[c]);
            if (!groupRoles.length) return null;
            return (
              <div key={group.label}>
                <p className="text-xs font-semibold text-[#94A3B8] uppercase tracking-wider mb-2">
                  {group.label}
                </p>
                <div className="space-y-1">
                  {groupRoles.map(code => (
                    <label
                      key={code}
                      className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-50 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selected.has(code)}
                        onChange={() => toggle(code)}
                        className="w-4 h-4 accent-[#2563EB]"
                      />
                      <span className="text-sm text-[#1E293B]">{roleMap[code]}</span>
                      <span className="ml-auto text-xs text-[#94A3B8] font-mono">{code}</span>
                    </label>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        <div className="flex gap-2 mt-6">
          <button
            onClick={() => mut.mutate(Array.from(selected))}
            disabled={mut.isPending}
            className="flex items-center gap-2 flex-1 justify-center py-2 bg-[#2563EB] text-white text-sm font-medium rounded-lg hover:bg-[#1D4ED8] disabled:opacity-50"
          >
            <Check className="w-4 h-4" />
            {mut.isPending ? 'Сохранение...' : 'Сохранить'}
          </button>
          <button onClick={onClose} className="px-4 py-2 border border-[#E2E8F0] rounded-lg text-sm text-[#64748B] hover:bg-gray-50">
            Отмена
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Главная страница ─────────────────────────────────────────────────────────

export function AdminPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [editRolesUser, setEditRolesUser] = useState<AppUser | null>(null);

  const { data: users = [], isLoading } = useQuery({ queryKey: ['admin-users'], queryFn: fetchUsers });
  const { data: allRoles = [] } = useQuery({ queryKey: ['admin-roles'], queryFn: fetchRoles });

  const deleteMut = useMutation({
    mutationFn: (id: number) => api.delete(`/auth/admin/users/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-users'] }),
  });

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-[#1E293B]">Пользователи</h1>
          <p className="text-sm text-[#64748B] mt-0.5">Управление доступом и ролями</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-[#2563EB] text-white text-sm font-medium rounded-lg hover:bg-[#1D4ED8] transition-colors"
        >
          <Plus className="w-4 h-4" />
          Создать
        </button>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-[#E2E8F0] overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-sm text-[#94A3B8]">Загрузка...</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#E2E8F0] bg-[#F8FAFC]">
                <th className="text-left px-4 py-3 text-xs font-semibold text-[#64748B] uppercase tracking-wider">Пользователь</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-[#64748B] uppercase tracking-wider">Email</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-[#64748B] uppercase tracking-wider">Роли</th>
                <th className="px-4 py-3 w-24" />
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.user_id} className="border-b border-[#F1F5F9] last:border-0 hover:bg-[#F8FAFC]">
                  <td className="px-4 py-3 font-medium text-[#1E293B]">{u.full_name}</td>
                  <td className="px-4 py-3 text-[#64748B]">{u.email}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {(u.roles ?? []).length === 0 ? (
                        <span className="text-xs text-[#94A3B8]">Нет ролей</span>
                      ) : (
                        (u.roles ?? []).map(r => (
                          <span key={r} className="px-2 py-0.5 bg-[#EFF6FF] text-[#2563EB] text-xs rounded-full font-medium">
                            {r}
                          </span>
                        ))
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 justify-end">
                      <button
                        onClick={() => setEditRolesUser(u)}
                        title="Редактировать роли"
                        className="p-1.5 rounded-lg text-[#64748B] hover:bg-[#EFF6FF] hover:text-[#2563EB] transition-colors"
                      >
                        <ShieldCheck className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setEditRolesUser(u)}
                        title="Редактировать"
                        className="p-1.5 rounded-lg text-[#64748B] hover:bg-gray-100 transition-colors"
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => {
                          if (confirm(`Удалить пользователя ${u.full_name}?`))
                            deleteMut.mutate(u.user_id);
                        }}
                        title="Удалить"
                        className="p-1.5 rounded-lg text-[#64748B] hover:bg-red-50 hover:text-red-500 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modals */}
      {showCreate && <CreateUserModal onClose={() => setShowCreate(false)} />}
      {editRolesUser && (
        <RolesPanel
          user={editRolesUser}
          allRoles={allRoles}
          onClose={() => setEditRolesUser(null)}
        />
      )}
    </div>
  );
}
