import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  FileText,
  AlertTriangle,
  RefreshCw,
  Bell,
  Settings,
  Megaphone,
  CalendarDays,
  LayoutList,
  Rss,
  Sparkles,
  FlaskConical,
  ShoppingCart,
  ShieldCheck,
  LogOut,
  Building2,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const legalNav = [
  { name: 'Дашборд',      href: '/',              icon: LayoutDashboard },
  { name: 'Договоры',     href: '/contracts',     icon: FileText },
  { name: 'Риски',        href: '/issues',        icon: AlertTriangle },
  { name: 'Интеграции',   href: '/integrations',  icon: RefreshCw },
  { name: 'Уведомления',  href: '/notifications', icon: Bell },
];

const marketingNav = [
  { name: 'Обзор',     href: '/marketing',          icon: Megaphone },
  { name: 'Календарь', href: '/marketing/calendar',  icon: CalendarDays },
  { name: 'Посты',     href: '/marketing/posts',     icon: LayoutList },
  { name: 'Источники', href: '/marketing/sources',   icon: Rss },
  { name: 'ИИ / План', href: '/marketing/ai',        icon: Sparkles },
];

const quarantineNav = [
  { name: 'Карантин', href: '/quarantine', icon: FlaskConical },
];

const procurementNav = [
  { name: 'Закупки', href: '/procurement', icon: ShoppingCart },
];

const oksNav = [
  { name: 'Объекты', href: '/oks', icon: Building2 },
];

function NavItem({ item }: { item: { name: string; href: string; icon: React.ElementType } }) {
  return (
    <NavLink
      to={item.href}
      end={item.href === '/' || item.href === '/marketing' || item.href === '/oks'}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
          isActive
            ? 'bg-[#2563EB] text-white'
            : 'text-[#64748B] hover:bg-gray-100 hover:text-[#1E293B]'
        }`
      }
    >
      <item.icon className="w-5 h-5" />
      {item.name}
    </NavLink>
  );
}

function NavSection({ title, items }: { title: string; items: typeof legalNav }) {
  return (
    <div>
      <p className="px-3 mb-2 text-xs font-semibold text-[#94A3B8] uppercase tracking-wider">
        {title}
      </p>
      <div className="space-y-0.5">
        {items.map((item) => <NavItem key={item.name} item={item} />)}
      </div>
    </div>
  );
}

export function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const isAdmin = user?.roles?.includes('admin');

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-white border-r border-[#E2E8F0] flex flex-col">
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b border-[#E2E8F0]">
        <span className="text-xl font-bold text-[#2563EB]">BioFabric</span>
        <span className="ml-2 text-sm text-[#64748B]">ERP</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-4 overflow-y-auto space-y-5">
        <NavSection title="Юридический" items={legalNav} />
        <div className="border-t border-[#E2E8F0]" />
        <NavSection title="Маркетинг" items={marketingNav} />
        <div className="border-t border-[#E2E8F0]" />
        <NavSection title="Виварий" items={quarantineNav} />
        <div className="border-t border-[#E2E8F0]" />
        <NavSection title="Снабжение" items={procurementNav} />
        <div className="border-t border-[#E2E8F0]" />
        <NavSection title="ОКС" items={oksNav} />
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-[#E2E8F0] space-y-1">
        {/* Current user */}
        {user && (
          <div className="px-3 py-2 mb-1">
            <p className="text-sm font-medium text-[#1E293B] truncate">{user.full_name}</p>
            <p className="text-xs text-[#94A3B8] truncate">{user.email}</p>
          </div>
        )}

        {/* Admin link */}
        {isAdmin && (
          <NavLink
            to="/admin"
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-[#2563EB] text-white'
                  : 'text-[#64748B] hover:bg-gray-100 hover:text-[#1E293B]'
              }`
            }
          >
            <ShieldCheck className="w-5 h-5" />
            Администратор
          </NavLink>
        )}

        {/* Settings */}
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              isActive
                ? 'bg-[#2563EB] text-white'
                : 'text-[#64748B] hover:bg-gray-100 hover:text-[#1E293B]'
            }`
          }
        >
          <Settings className="w-5 h-5" />
          Настройки
        </NavLink>

        {/* Logout */}
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-[#64748B] hover:bg-red-50 hover:text-red-500 transition-colors"
        >
          <LogOut className="w-5 h-5" />
          Выйти
        </button>
      </div>
    </aside>
  );
}
