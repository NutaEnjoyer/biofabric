import { NavLink } from 'react-router-dom';
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
} from 'lucide-react';

const legalNav = [
  { name: 'Дашборд', href: '/', icon: LayoutDashboard },
  { name: 'Договоры', href: '/contracts', icon: FileText },
  { name: 'Риски', href: '/issues', icon: AlertTriangle },
  { name: 'Интеграции', href: '/integrations', icon: RefreshCw },
  { name: 'Уведомления', href: '/notifications', icon: Bell },
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

function NavItem({ item }: { item: { name: string; href: string; icon: React.ElementType } }) {
  return (
    <NavLink
      to={item.href}
      end={item.href === '/' || item.href === '/marketing'}
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

export function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-white border-r border-[#E2E8F0] flex flex-col">
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b border-[#E2E8F0]">
        <span className="text-xl font-bold text-[#2563EB]">BioFabric</span>
        <span className="ml-2 text-sm text-[#64748B]">ERP</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-4 overflow-y-auto space-y-5">
        {/* Legal section */}
        <div>
          <p className="px-3 mb-2 text-xs font-semibold text-[#94A3B8] uppercase tracking-wider">
            Юридический
          </p>
          <div className="space-y-0.5">
            {legalNav.map((item) => <NavItem key={item.name} item={item} />)}
          </div>
        </div>

        {/* Divider */}
        <div className="border-t border-[#E2E8F0]" />

        {/* Marketing section */}
        <div>
          <p className="px-3 mb-2 text-xs font-semibold text-[#94A3B8] uppercase tracking-wider">
            Маркетинг
          </p>
          <div className="space-y-0.5">
            {marketingNav.map((item) => <NavItem key={item.name} item={item} />)}
          </div>
        </div>

        {/* Divider */}
        <div className="border-t border-[#E2E8F0]" />

        {/* Quarantine section */}
        <div>
          <p className="px-3 mb-2 text-xs font-semibold text-[#94A3B8] uppercase tracking-wider">
            Виварий
          </p>
          <div className="space-y-0.5">
            {quarantineNav.map((item) => <NavItem key={item.name} item={item} />)}
          </div>
        </div>

        {/* Divider */}
        <div className="border-t border-[#E2E8F0]" />

        {/* Procurement section */}
        <div>
          <p className="px-3 mb-2 text-xs font-semibold text-[#94A3B8] uppercase tracking-wider">
            Снабжение
          </p>
          <div className="space-y-0.5">
            {procurementNav.map((item) => <NavItem key={item.name} item={item} />)}
          </div>
        </div>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-[#E2E8F0]">
        <NavLink
          to="/settings"
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-[#64748B] hover:bg-gray-100 hover:text-[#1E293B] transition-colors"
        >
          <Settings className="w-5 h-5" />
          Настройки
        </NavLink>
      </div>
    </aside>
  );
}
