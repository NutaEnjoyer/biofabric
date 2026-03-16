import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle, XCircle, RotateCcw, ChevronRight, FileText, Package } from 'lucide-react';
import { Card, CardHeader, CardContent, Button, Badge, Modal, Input, Select } from '../../components/ui';
import {
  useRequest, usePatchStatus, useAddApproval, useAddQuote, useAddDocument,
} from '../../hooks/useProcurement';
import type { ProcurementStatus, ApprovalDecision, Approval, SupplierQuote, ProcurementDocument } from '../../types/procurement';

const STATUS_BADGE: Record<ProcurementStatus, { variant: 'default' | 'warning' | 'info' | 'success' | 'danger'; label: string }> = {
  draft:             { variant: 'default',  label: 'Черновик' },
  on_approval:       { variant: 'warning',  label: 'На согласовании' },
  in_progress:       { variant: 'info',     label: 'На исполнении' },
  awaiting_delivery: { variant: 'warning',  label: 'Ожидание поставки' },
  done:              { variant: 'success',  label: 'Исполнена' },
  overdue:           { variant: 'danger',   label: 'Просрочена' },
};

const NEXT_STATUSES: Partial<Record<ProcurementStatus, ProcurementStatus[]>> = {
  draft:             ['on_approval'],
  on_approval:       ['in_progress', 'draft'],
  in_progress:       ['awaiting_delivery'],
  awaiting_delivery: ['done'],
};

const STATUS_LABELS: Record<ProcurementStatus, string> = {
  draft:             'Черновик',
  on_approval:       'На согласовании',
  in_progress:       'На исполнении',
  awaiting_delivery: 'Ожидание поставки',
  done:              'Исполнена',
  overdue:           'Просрочена',
};

const DECISION_OPTIONS = [
  { value: 'approve', label: 'Утвердить' },
  { value: 'reject', label: 'Отклонить' },
  { value: 'return_for_rework', label: 'Вернуть на доработку' },
];

const DOC_TYPE_OPTIONS = [
  { value: 'ТЗ', label: 'Техническое задание' },
  { value: 'КП', label: 'Коммерческое предложение' },
  { value: 'договор', label: 'Договор' },
  { value: 'счёт', label: 'Счёт' },
  { value: 'акт', label: 'Акт' },
  { value: 'накладная', label: 'Накладная' },
];

function DecisionBadge({ decision }: { decision: ApprovalDecision }) {
  if (decision === 'approve') return <Badge variant="success">Утверждено</Badge>;
  if (decision === 'reject') return <Badge variant="danger">Отклонено</Badge>;
  return <Badge variant="warning">На доработку</Badge>;
}

export function ProcurementDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const reqId = Number(id);

  const { data: req, isLoading } = useRequest(reqId);
  const patchStatus = usePatchStatus();
  const addApproval = useAddApproval();
  const addQuote = useAddQuote();
  const addDocument = useAddDocument();

  // Modals
  const [approvalOpen, setApprovalOpen] = useState(false);
  const [quoteOpen, setQuoteOpen] = useState(false);
  const [docOpen, setDocOpen] = useState(false);

  // Approval form
  const [approvalDecision, setApprovalDecision] = useState<ApprovalDecision>('approve');
  const [approvalComment, setApprovalComment] = useState('');
  const [approvalUserId, setApprovalUserId] = useState('');

  // Quote form
  const [supplierName, setSupplierName] = useState('');
  const [price, setPrice] = useState('');
  const [deliveryDays, setDeliveryDays] = useState('');
  const [quoteComment, setQuoteComment] = useState('');

  // Document form
  const [docType, setDocType] = useState('ТЗ');
  const [docFilename, setDocFilename] = useState('');
  const [docUrl, setDocUrl] = useState('');
  const [docSigned, setDocSigned] = useState(false);

  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const flash = (msg: string) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(null), 4000);
  };

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-[#64748B]">Загрузка...</div>;
  }
  if (!req) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <p className="text-[#64748B] mb-4">Заявка не найдена</p>
        <Button onClick={() => navigate('/procurement')}>Назад к списку</Button>
      </div>
    );
  }

  const statusCfg = STATUS_BADGE[req.status] || { variant: 'default' as const, label: req.status };
  const nextStatuses = NEXT_STATUSES[req.status] || [];

  const handleStatusChange = async (status: ProcurementStatus) => {
    await patchStatus.mutateAsync({ id: reqId, status });
    flash(`Статус изменён: ${STATUS_LABELS[status]}`);
  };

  const handleApproval = async () => {
    await addApproval.mutateAsync({
      request_id: reqId,
      user_id: Number(approvalUserId) || 1,
      decision: approvalDecision,
      comment: approvalComment || undefined,
    });
    setApprovalOpen(false);
    setApprovalComment('');
    flash('Решение по согласованию добавлено');
  };

  const handleQuote = async () => {
    await addQuote.mutateAsync({
      request_id: reqId,
      supplier_name: supplierName,
      price: Number(price),
      delivery_days: deliveryDays ? Number(deliveryDays) : undefined,
      comment: quoteComment || undefined,
    });
    setQuoteOpen(false);
    setSupplierName('');
    setPrice('');
    setDeliveryDays('');
    setQuoteComment('');
    flash('Коммерческое предложение добавлено');
  };

  const handleDocument = async () => {
    await addDocument.mutateAsync({
      request_id: reqId,
      doc_type: docType,
      filename: docFilename,
      storage_url: docUrl || undefined,
      signed: docSigned,
    });
    setDocOpen(false);
    setDocFilename('');
    setDocUrl('');
    setDocSigned(false);
    flash('Документ прикреплён');
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <button
          onClick={() => navigate('/procurement')}
          className="p-2 rounded-lg hover:bg-gray-100 text-[#64748B] transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-[#1E293B]">Заявка #{req.id}</h1>
            <Badge variant={statusCfg.variant}>{statusCfg.label}</Badge>
          </div>
          <p className="text-[#64748B] mt-1">{req.subject}</p>
        </div>
      </div>

      {successMsg && (
        <div className="mb-6 p-4 bg-[#ECFDF5] border border-[#10B981] rounded-lg text-[#10B981]">
          {successMsg}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: main content */}
        <div className="lg:col-span-2 space-y-6">

          {/* Basic info */}
          <Card>
            <CardHeader title="Основная информация" />
            <CardContent>
              <dl className="grid grid-cols-2 gap-x-6 gap-y-4">
                <div>
                  <dt className="text-sm text-[#64748B]">Создана</dt>
                  <dd className="text-sm font-medium text-[#1E293B] mt-1">
                    {new Date(req.created_at).toLocaleDateString('ru-RU')}
                  </dd>
                </div>
                {req.justification && (
                  <div className="col-span-2">
                    <dt className="text-sm text-[#64748B]">Обоснование</dt>
                    <dd className="text-sm text-[#1E293B] mt-1">{req.justification}</dd>
                  </div>
                )}
              </dl>
            </CardContent>
          </Card>

          {/* Items */}
          {req.items && req.items.length > 0 && (
            <Card>
              <CardHeader title="Позиции" description={`${req.items.length} позиций`} />
              <CardContent className="p-0">
                <div className="divide-y divide-[#E2E8F0]">
                  {req.items.map((item) => (
                    <div key={item.id} className="px-6 py-4 flex items-start gap-4">
                      <Package className="w-4 h-4 text-[#64748B] mt-0.5 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-[#1E293B]">{item.nomenclature}</p>
                        {item.tech_spec && (
                          <p className="text-sm text-[#64748B] mt-0.5">{item.tech_spec}</p>
                        )}
                      </div>
                      <div className="text-right flex-shrink-0">
                        <p className="text-sm font-medium">{item.quantity} шт.</p>
                        {item.due_days && (
                          <p className="text-xs text-[#64748B]">{item.due_days} дн.</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Approvals */}
          <Card>
            <CardHeader
              title="Согласования"
              description={`${req.approvals?.length || 0} решений`}
              action={
                <Button size="sm" variant="secondary" onClick={() => setApprovalOpen(true)}>
                  Добавить решение
                </Button>
              }
            />
            <CardContent className="p-0">
              {req.approvals && req.approvals.length > 0 ? (
                <div className="divide-y divide-[#E2E8F0]">
                  {req.approvals.map((a: Approval) => (
                    <div key={a.id} className="px-6 py-4 flex items-start gap-4">
                      {a.decision === 'approve' ? (
                        <CheckCircle className="w-5 h-5 text-[#10B981] flex-shrink-0" />
                      ) : a.decision === 'reject' ? (
                        <XCircle className="w-5 h-5 text-[#EF4444] flex-shrink-0" />
                      ) : (
                        <RotateCcw className="w-5 h-5 text-[#F59E0B] flex-shrink-0" />
                      )}
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <DecisionBadge decision={a.decision} />
                          <span className="text-xs text-[#64748B]">
                            {new Date(a.decided_at).toLocaleDateString('ru-RU')}
                          </span>
                        </div>
                        {a.comment && <p className="text-sm text-[#64748B] mt-1">{a.comment}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-8 text-center text-sm text-[#64748B]">Решений ещё нет</div>
              )}
            </CardContent>
          </Card>

          {/* Supplier quotes */}
          <Card>
            <CardHeader
              title="Коммерческие предложения"
              description={`${req.quotes?.length || 0} КП`}
              action={
                <Button size="sm" variant="secondary" onClick={() => setQuoteOpen(true)}>
                  Добавить КП
                </Button>
              }
            />
            <CardContent className="p-0">
              {req.quotes && req.quotes.length > 0 ? (
                <div className="divide-y divide-[#E2E8F0]">
                  {req.quotes.map((q: SupplierQuote) => (
                    <div key={q.id} className="px-6 py-4 flex items-center gap-4">
                      <div className="flex-1">
                        <p className="text-sm font-medium text-[#1E293B]">{q.supplier_name}</p>
                        {q.comment && <p className="text-xs text-[#64748B] mt-0.5">{q.comment}</p>}
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-semibold">
                          {new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB' }).format(q.price)}
                        </p>
                        {q.delivery_days && (
                          <p className="text-xs text-[#64748B]">{q.delivery_days} дн. доставки</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-8 text-center text-sm text-[#64748B]">КП не добавлены</div>
              )}
            </CardContent>
          </Card>

          {/* Documents */}
          <Card>
            <CardHeader
              title="Документы"
              description={`${req.documents?.length || 0} файлов`}
              action={
                <Button size="sm" variant="secondary" onClick={() => setDocOpen(true)}>
                  Прикрепить
                </Button>
              }
            />
            <CardContent className="p-0">
              {req.documents && req.documents.length > 0 ? (
                <div className="divide-y divide-[#E2E8F0]">
                  {req.documents.map((d: ProcurementDocument) => (
                    <div key={d.id} className="px-6 py-4 flex items-center gap-4">
                      <FileText className="w-4 h-4 text-[#64748B] flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-[#1E293B] truncate">{d.filename}</p>
                        <p className="text-xs text-[#64748B]">{d.doc_type}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        {d.signed && <Badge variant="success">Подписан</Badge>}
                        {d.storage_url && (
                          <a
                            href={d.storage_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-[#2563EB] hover:underline text-sm"
                          >
                            Открыть
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-8 text-center text-sm text-[#64748B]">Документы не прикреплены</div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right: actions */}
        <div>
          <Card>
            <CardHeader title="Действия" />
            <CardContent className="space-y-3">
              {nextStatuses.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-medium text-[#64748B] uppercase tracking-wider">Перевести статус</p>
                  {nextStatuses.map((s) => (
                    <Button
                      key={s}
                      variant="secondary"
                      className="w-full justify-between"
                      onClick={() => handleStatusChange(s)}
                      loading={patchStatus.isPending}
                    >
                      {STATUS_LABELS[s]}
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  ))}
                </div>
              )}
              {req.status === 'done' && (
                <div className="p-3 bg-[#ECFDF5] rounded-lg text-sm text-[#10B981] text-center">
                  Заявка исполнена
                </div>
              )}
            </CardContent>
          </Card>

          {/* Events */}
          {req.events && req.events.length > 0 && (
            <Card className="mt-6">
              <CardHeader title="История" />
              <CardContent className="p-0">
                <div className="divide-y divide-[#E2E8F0]">
                  {req.events.map((ev) => (
                    <div key={ev.id} className="px-4 py-3">
                      <p className="text-xs font-medium text-[#1E293B]">{ev.event_type}</p>
                      <p className="text-xs text-[#64748B] mt-0.5">
                        {new Date(ev.created_at).toLocaleString('ru-RU')}
                      </p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Approval modal */}
      <Modal isOpen={approvalOpen} onClose={() => setApprovalOpen(false)} title="Добавить решение по согласованию">
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-[#64748B] mb-1">ID пользователя</label>
            <Input
              type="number"
              placeholder="1"
              value={approvalUserId}
              onChange={(e) => setApprovalUserId(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm text-[#64748B] mb-1">Решение</label>
            <Select
              options={DECISION_OPTIONS}
              value={approvalDecision}
              onChange={(e) => setApprovalDecision(e.target.value as ApprovalDecision)}
            />
          </div>
          <div>
            <label className="block text-sm text-[#64748B] mb-1">Комментарий</label>
            <Input
              placeholder="Необязательно"
              value={approvalComment}
              onChange={(e) => setApprovalComment(e.target.value)}
            />
          </div>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <Button variant="secondary" onClick={() => setApprovalOpen(false)}>Отмена</Button>
          <Button onClick={handleApproval} loading={addApproval.isPending}>Сохранить</Button>
        </div>
      </Modal>

      {/* Quote modal */}
      <Modal isOpen={quoteOpen} onClose={() => setQuoteOpen(false)} title="Коммерческое предложение">
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-[#64748B] mb-1">Поставщик *</label>
            <Input
              placeholder="Название компании"
              value={supplierName}
              onChange={(e) => setSupplierName(e.target.value)}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-[#64748B] mb-1">Цена *</label>
              <Input
                type="number"
                min={0}
                placeholder="0"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm text-[#64748B] mb-1">Срок доставки (дн.)</label>
              <Input
                type="number"
                min={1}
                placeholder="—"
                value={deliveryDays}
                onChange={(e) => setDeliveryDays(e.target.value)}
              />
            </div>
          </div>
          <div>
            <label className="block text-sm text-[#64748B] mb-1">Комментарий</label>
            <Input
              placeholder="Необязательно"
              value={quoteComment}
              onChange={(e) => setQuoteComment(e.target.value)}
            />
          </div>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <Button variant="secondary" onClick={() => setQuoteOpen(false)}>Отмена</Button>
          <Button onClick={handleQuote} loading={addQuote.isPending} disabled={!supplierName || !price}>
            Добавить
          </Button>
        </div>
      </Modal>

      {/* Document modal */}
      <Modal isOpen={docOpen} onClose={() => setDocOpen(false)} title="Прикрепить документ">
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-[#64748B] mb-1">Тип документа</label>
            <Select
              options={DOC_TYPE_OPTIONS}
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm text-[#64748B] mb-1">Имя файла *</label>
            <Input
              placeholder="contract.pdf"
              value={docFilename}
              onChange={(e) => setDocFilename(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm text-[#64748B] mb-1">URL (необязательно)</label>
            <Input
              placeholder="https://..."
              value={docUrl}
              onChange={(e) => setDocUrl(e.target.value)}
            />
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={docSigned}
              onChange={(e) => setDocSigned(e.target.checked)}
              className="rounded"
            />
            <span className="text-sm text-[#1E293B]">Документ подписан</span>
          </label>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <Button variant="secondary" onClick={() => setDocOpen(false)}>Отмена</Button>
          <Button onClick={handleDocument} loading={addDocument.isPending} disabled={!docFilename}>
            Прикрепить
          </Button>
        </div>
      </Modal>
    </div>
  );
}
