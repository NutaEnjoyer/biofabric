type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info';

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
}

const variants: Record<BadgeVariant, string> = {
  default: 'bg-gray-100 text-gray-700',
  success: 'bg-[#ECFDF5] text-[#10B981]',
  warning: 'bg-[#FFFBEB] text-[#F59E0B]',
  danger: 'bg-[#FEF2F2] text-[#EF4444]',
  info: 'bg-blue-50 text-[#2563EB]',
};

export function Badge({ variant = 'default', children }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${variants[variant]}`}>
      {children}
    </span>
  );
}

// Helper for contract status
export function StatusBadge({ status }: { status: string }) {
  const statusMap: Record<string, { variant: BadgeVariant; label: string }> = {
    draft: { variant: 'default', label: 'Черновик' },
    pending: { variant: 'warning', label: 'На согласовании' },
    active: { variant: 'success', label: 'Активен' },
    completed: { variant: 'info', label: 'Завершён' },
    terminated: { variant: 'danger', label: 'Расторгнут' },
    overdue: { variant: 'danger', label: 'Просрочен' },
    archived: { variant: 'default', label: 'Архив' },
  };

  const config = statusMap[status] || { variant: 'default' as BadgeVariant, label: status };
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
