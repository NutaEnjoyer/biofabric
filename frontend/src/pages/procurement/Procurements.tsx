import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PlusCircle, Filter } from 'lucide-react';
import { Card, CardHeader, CardContent, Button, Modal, Input, Select, Table, Badge } from '../../components/ui';
import { useRequests, useCreateRequest } from '../../hooks/useProcurement';
import type { ProcurementRequest, ProcurementStatus, RequestItemIn } from '../../types/procurement';

const STATUS_OPTIONS = [
  { value: '', label: 'Все статусы' },
  { value: 'draft', label: 'Черновик' },
  { value: 'on_approval', label: 'На согласовании' },
  { value: 'in_progress', label: 'На исполнении' },
  { value: 'awaiting_delivery', label: 'Ожидание поставки' },
  { value: 'done', label: 'Исполнена' },
  { value: 'overdue', label: 'Просрочена' },
];

const STATUS_BADGE: Record<ProcurementStatus, { variant: 'default' | 'warning' | 'info' | 'success' | 'danger'; label: string }> = {
  draft:             { variant: 'default',  label: 'Черновик' },
  on_approval:       { variant: 'warning',  label: 'На согласовании' },
  in_progress:       { variant: 'info',     label: 'На исполнении' },
  awaiting_delivery: { variant: 'warning',  label: 'Ожидание поставки' },
  done:              { variant: 'success',  label: 'Исполнена' },
  overdue:           { variant: 'danger',   label: 'Просрочена' },
};

function ProcurementBadge({ status }: { status: ProcurementStatus }) {
  const cfg = STATUS_BADGE[status] || { variant: 'default' as const, label: status };
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>;
}

const emptyItem = (): RequestItemIn => ({ nomenclature: '', quantity: 1 });

export function Procurements() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState<ProcurementStatus | ''>('');
  const [modalOpen, setModalOpen] = useState(false);
  const [subject, setSubject] = useState('');
  const [justification, setJustification] = useState('');
  const [items, setItems] = useState<RequestItemIn[]>([emptyItem()]);

  const { data = [], isLoading } = useRequests(statusFilter || undefined);
  const createRequest = useCreateRequest();

  const updateItem = (idx: number, field: keyof RequestItemIn, value: string | number) => {
    setItems((prev) => prev.map((it, i) => (i === idx ? { ...it, [field]: value } : it)));
  };

  const handleCreate = async () => {
    if (!subject.trim()) return;
    const validItems = items.filter((it) => it.nomenclature.trim());
    await createRequest.mutateAsync({ subject, justification: justification || undefined, items: validItems });
    setModalOpen(false);
    setSubject('');
    setJustification('');
    setItems([emptyItem()]);
  };

  const columns = [
    {
      key: 'id',
      header: '№',
      render: (r: ProcurementRequest) => <span className="font-medium text-[#2563EB]">#{r.id}</span>,
    },
    {
      key: 'subject',
      header: 'Предмет закупки',
      render: (r: ProcurementRequest) => <span className="font-medium">{r.subject}</span>,
    },
    {
      key: 'status',
      header: 'Статус',
      render: (r: ProcurementRequest) => <ProcurementBadge status={r.status} />,
    },
    {
      key: 'created_at',
      header: 'Создана',
      render: (r: ProcurementRequest) =>
        new Date(r.created_at).toLocaleDateString('ru-RU'),
    },
    {
      key: 'items',
      header: 'Позиций',
      render: (r: ProcurementRequest) => r.items?.length ?? '—',
      className: 'text-right',
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-[#1E293B]">Закупки</h1>
          <p className="text-[#64748B] mt-1">Заявки на приобретение товаров и услуг</p>
        </div>
        <Button onClick={() => setModalOpen(true)}>
          <PlusCircle className="w-4 h-4" />
          Новая заявка
        </Button>
      </div>

      <Card>
        <CardHeader
          title="Список заявок"
          description={`Найдено: ${data.length}`}
          action={
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-[#64748B]" />
              <Select
                options={STATUS_OPTIONS}
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as ProcurementStatus | '')}
                className="w-52"
              />
            </div>
          }
        />
        <CardContent className="p-0">
          <Table
            columns={columns}
            data={data}
            keyExtractor={(r) => r.id}
            onRowClick={(r) => navigate(`/procurement/${r.id}`)}
            loading={isLoading}
            emptyMessage="Заявки не найдены"
          />
        </CardContent>
      </Card>

      {/* Create modal */}
      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Новая заявка на закупку" size="lg">
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-[#64748B] mb-1">Предмет закупки *</label>
            <Input
              placeholder="Краткое название закупки"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm text-[#64748B] mb-1">Обоснование</label>
            <Input
              placeholder="Зачем нужна закупка"
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm text-[#64748B]">Позиции</label>
              <button
                onClick={() => setItems((prev) => [...prev, emptyItem()])}
                className="text-sm text-[#2563EB] hover:underline"
              >
                + Добавить позицию
              </button>
            </div>
            <div className="space-y-3">
              {items.map((item, idx) => (
                <div key={idx} className="flex gap-3 items-start">
                  <div className="flex-1">
                    <Input
                      placeholder="Наименование *"
                      value={item.nomenclature}
                      onChange={(e) => updateItem(idx, 'nomenclature', e.target.value)}
                    />
                  </div>
                  <div className="w-24">
                    <Input
                      type="number"
                      min={0.01}
                      step={0.01}
                      placeholder="Кол-во"
                      value={item.quantity}
                      onChange={(e) => updateItem(idx, 'quantity', Number(e.target.value))}
                    />
                  </div>
                  <div className="w-24">
                    <Input
                      type="number"
                      min={1}
                      placeholder="Дней"
                      value={item.due_days || ''}
                      onChange={(e) => updateItem(idx, 'due_days', Number(e.target.value))}
                    />
                  </div>
                  {items.length > 1 && (
                    <button
                      onClick={() => setItems((prev) => prev.filter((_, i) => i !== idx))}
                      className="mt-2 text-[#64748B] hover:text-[#EF4444] transition-colors text-lg leading-none"
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <Button variant="secondary" onClick={() => setModalOpen(false)}>Отмена</Button>
          <Button onClick={handleCreate} loading={createRequest.isPending} disabled={!subject.trim()}>
            Создать заявку
          </Button>
        </div>
      </Modal>
    </div>
  );
}
