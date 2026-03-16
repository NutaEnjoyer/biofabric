import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Filter } from 'lucide-react';
import { Card, CardHeader, CardContent, Table, Select, StatusBadge, Badge } from '../components/ui';
import { useContracts } from '../hooks/useContracts';
import type { ContractShort } from '../types/contracts';

const statusOptions = [
  { value: '', label: 'Все статусы' },
  { value: 'draft', label: 'Черновик' },
  { value: 'legal_review', label: 'На проверке' },
  { value: 'approved', label: 'Утверждён' },
  { value: 'active', label: 'Действует' },
  { value: 'completed', label: 'Исполнен' },
  { value: 'overdue', label: 'Просрочен' },
  { value: 'terminated', label: 'Расторгнут' },
];

// Визуальные индикаторы (ТЗ п.3)
function ContractIndicators({ item }: { item: ContractShort }) {
  const dots: { icon: string; title: string }[] = [];

  if (item.is_overdue_flag || item.status_code === 'overdue') {
    dots.push({ icon: '🔴', title: 'Просрочен — нарушены сроки исполнения' });
  }
  if (item.has_active_guarantee === false) {
    dots.push({ icon: '🟡', title: 'Без активной банковской гарантии' });
  }
  if (item.has_deviations) {
    dots.push({ icon: '🔵', title: 'Есть отклонения от шаблона' });
  }
  if (
    (item.status_code === 'approved' || item.status_code === 'active') &&
    !item.is_overdue_flag &&
    !item.has_deviations
  ) {
    dots.push({ icon: '🟢', title: 'Проверен / согласован' });
  }

  if (dots.length === 0) return null;

  return (
    <div className="flex items-center gap-1">
      {dots.map((d, i) => (
        <span key={i} title={d.title} className="text-sm cursor-help">
          {d.icon}
        </span>
      ))}
    </div>
  );
}

// Бейдж источника договора (ТЗ п.6)
function SourceBadge({ source }: { source?: string }) {
  if (!source || source === 'manual') {
    return <Badge variant="default">Вручную</Badge>;
  }
  return <Badge variant="info">1С</Badge>;
}

export function Contracts() {
  const [statusFilter, setStatusFilter] = useState('');
  const navigate = useNavigate();
  const { data, isLoading } = useContracts({
    status_code: statusFilter || undefined,
    limit: 100,
  });

  const columns = [
    {
      key: 'indicators',
      header: '',
      render: (item: ContractShort) => <ContractIndicators item={item} />,
      className: 'w-24',
    },
    {
      key: 'contract_no',
      header: '№ договора',
      render: (item: ContractShort) => (
        <span className="font-medium">{item.contract_no}</span>
      ),
    },
    {
      key: 'title',
      header: 'Название',
    },
    {
      key: 'status_code',
      header: 'Статус',
      render: (item: ContractShort) => <StatusBadge status={item.status_code || 'draft'} />,
    },
    {
      key: 'source_code',
      header: 'Источник',
      render: (item: ContractShort) => <SourceBadge source={item.source_code} />,
    },
    {
      key: 'end_date',
      header: 'Дата окончания',
      render: (item: ContractShort) => {
        if (!item.end_date) return '—';
        const isOverdue = new Date(item.end_date) < new Date() && item.status_code !== 'completed';
        return (
          <span className={isOverdue ? 'text-[#EF4444] font-medium' : undefined}>
            {item.end_date}
          </span>
        );
      },
    },
    {
      key: 'amount_total',
      header: 'Сумма',
      render: (item: ContractShort) =>
        item.amount_total
          ? new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB' }).format(item.amount_total)
          : '—',
      className: 'text-right',
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-[#1E293B]">Договоры</h1>
          <p className="text-[#64748B] mt-1">Реестр договоров компании</p>
        </div>
      </div>

      {/* Легенда индикаторов */}
      <div className="flex items-center gap-4 mb-4 text-xs text-[#64748B]">
        <span>Индикаторы:</span>
        <span title="Просрочен">🔴 Просрочен</span>
        <span title="Без активной гарантии">🟡 Без гарантии</span>
        <span title="Есть отклонения">🔵 Отклонения</span>
        <span title="Проверен / согласован">🟢 Согласован</span>
      </div>

      <Card>
        <CardHeader
          title="Список договоров"
          description={`Найдено: ${data?.count || 0}`}
          action={
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-[#64748B]" />
                <Select
                  options={statusOptions}
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="w-48"
                />
              </div>
            </div>
          }
        />
        <CardContent className="p-0">
          <Table
            columns={columns}
            data={data?.items || []}
            keyExtractor={(item) => item.contract_id}
            onRowClick={(item) => navigate(`/contracts/${item.contract_id}`)}
            loading={isLoading}
            emptyMessage="Договоры не найдены"
          />
        </CardContent>
      </Card>
    </div>
  );
}
