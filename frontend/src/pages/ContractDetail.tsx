import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Play, RefreshCw, UserCheck, Send, Brain } from 'lucide-react';
import { Card, CardHeader, CardContent, Button, StatusBadge, Badge } from '../components/ui';
import {
  useContract,
  useBindWorkflow,
  useSyncDeadlines,
  useValidateParties,
  useContractTimeline,
  useContractAIAnalysis,
  useStartAIAnalysis,
  useSendTo1C,
} from '../hooks/useContracts';
import { useState, useEffect } from 'react';
import type { TimelineEntry, ContractAIAnalysis } from '../types/contracts';

// ─── Вспомогательные компоненты ──────────────────────────────────────────────

function Skeleton({ className }: { className: string }) {
  return <div className={`animate-pulse bg-gray-200 rounded ${className}`} />;
}

function Toast({ msg, type }: { msg: string; type: 'success' | 'error' }) {
  return (
    <div
      className={`px-4 py-3 rounded-lg shadow-lg text-sm font-medium max-w-sm
        ${type === 'success' ? 'bg-[#ECFDF5] text-[#10B981] border border-[#10B981]' : 'bg-[#FEF2F2] text-[#EF4444] border border-[#EF4444]'}`}
    >
      {msg}
    </div>
  );
}

function SourceBadge({ source }: { source?: string }) {
  if (!source || source === 'manual') {
    return <Badge variant="default">Введён вручную</Badge>;
  }
  return <Badge variant="info">Импорт из 1С</Badge>;
}

function IntegrationStatusDot({ status }: { status: string }) {
  const map: Record<string, { color: string; label: string }> = {
    not_sent: { color: 'text-yellow-500', label: '🟡 Не отправлен' },
    queued:   { color: 'text-blue-500',   label: '🔵 В очереди' },
    sent:     { color: 'text-green-500',  label: '🟢 Отправлен' },
    error:    { color: 'text-red-500',    label: '🔴 Ошибка' },
  };
  const cfg = map[status] || map.not_sent;
  return <span className={`text-sm font-medium ${cfg.color}`}>{cfg.label}</span>;
}

function DeadlineRow({ label, date }: { label: string; date: string }) {
  const isOverdue = new Date(date) < new Date();
  return (
    <div className="flex items-center justify-between py-2 border-b border-[#E2E8F0] last:border-0">
      <span className="text-sm text-[#64748B]">{label}</span>
      <span className={`text-sm font-medium ${isOverdue ? 'text-[#EF4444]' : 'text-[#1E293B]'}`}>
        {date}
        {isOverdue && <span className="ml-2 text-xs text-[#EF4444]">Просрочен</span>}
      </span>
    </div>
  );
}

function AIAnalysisBlock({ analysis }: { analysis: ContractAIAnalysis }) {
  const statusLabels: Record<string, string> = {
    pending:      'Ожидает запуска',
    running:      'Выполняется...',
    done:         'Выполнен ✅',
    needs_rerun:  'Требует повторного анализа ⚠️',
    not_started:  'Не выполнялся',
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm text-[#64748B]">Статус</span>
        <span className="text-sm font-medium text-[#1E293B]">
          {statusLabels[analysis.status] || analysis.status}
        </span>
      </div>
      {analysis.analyzed_at && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-[#64748B]">Последний анализ</span>
          <span className="text-sm text-[#1E293B]">{analysis.analyzed_at.slice(0, 16).replace('T', ' ')}</span>
        </div>
      )}
      {analysis.status === 'done' && analysis.summary_text && (
        <div className="p-3 bg-gray-50 rounded-lg">
          <p className="text-sm text-[#1E293B]">{analysis.summary_text}</p>
        </div>
      )}
      {analysis.status === 'done' && (
        <div className="grid grid-cols-2 gap-3">
          <div className="text-center p-2 bg-gray-50 rounded-lg">
            <div className={`text-xl font-bold ${analysis.deviations_count > 0 ? 'text-[#2563EB]' : 'text-[#10B981]'}`}>
              {analysis.deviations_count}
            </div>
            <div className="text-xs text-[#64748B]">Отклонений</div>
          </div>
          <div className="text-center p-2 bg-gray-50 rounded-lg">
            <div className={`text-xl font-bold ${analysis.has_critical_risk ? 'text-[#EF4444]' : 'text-[#10B981]'}`}>
              {analysis.has_critical_risk ? '!' : '✓'}
            </div>
            <div className="text-xs text-[#64748B]">Критических рисков</div>
          </div>
        </div>
      )}
    </div>
  );
}

function TimelineList({ entries }: { entries: TimelineEntry[] }) {
  const fieldLabels: Record<string, string> = {
    status_code:            'Статус договора',
    integration_1c_status:  'Интеграция с 1С',
    ai_analysis:            'ИИ-анализ',
    amount_total:           'Сумма',
    end_date:               'Дата окончания',
    performance_due:        'Срок исполнения',
    payment_due:            'Срок оплаты',
  };

  return (
    <div className="relative">
      <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-[#E2E8F0]" />
      <div className="space-y-4">
        {entries.map((entry) => (
          <div key={entry.history_id} className="relative flex gap-4 pl-10">
            <div className="absolute left-2.5 top-1.5 w-3 h-3 rounded-full bg-[#2563EB] border-2 border-white shadow" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-[#1E293B]">
                  {fieldLabels[entry.field_name] || entry.field_name}
                </span>
                <span className="text-xs text-[#94A3B8] shrink-0">
                  {entry.changed_at.slice(0, 16).replace('T', ' ')}
                </span>
              </div>
              {(entry.old_value || entry.new_value) && (
                <div className="mt-1 text-xs text-[#64748B]">
                  {entry.old_value && <span className="line-through mr-2">{entry.old_value}</span>}
                  {entry.new_value && <span className="text-[#1E293B] font-medium">→ {entry.new_value}</span>}
                </div>
              )}
              {entry.reason && (
                <p className="mt-1 text-xs text-[#94A3B8]">{entry.reason}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Основной компонент ───────────────────────────────────────────────────────

export function ContractDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const contractId = Number(id);

  const { data: contract, isLoading } = useContract(contractId);
  const { data: timeline, isLoading: timelineLoading } = useContractTimeline(contractId);
  const { data: analysisData, refetch: refetchAnalysis } = useContractAIAnalysis(contractId);

  const bindWorkflow  = useBindWorkflow();
  const syncDeadlines = useSyncDeadlines();
  const validateParties = useValidateParties();
  const startAnalysis = useStartAIAnalysis();
  const sendTo1C      = useSendTo1C();

  const [validationResult, setValidationResult] = useState<string[] | null>(null);
  const [toasts, setToasts] = useState<{ id: number; msg: string; type: 'success' | 'error' }[]>([]);

  const addToast = (msg: string, type: 'success' | 'error' = 'success') => {
    const toastId = Date.now();
    setToasts(prev => [...prev, { id: toastId, msg, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== toastId)), 4000);
  };

  // Автозапуск ИИ-анализа при первой загрузке (ТЗ п.2 Вариант 1)
  const analysis = analysisData && 'analysis_id' in analysisData ? analysisData : null;
  const analysisNotStarted = !analysisData || ('status' in analysisData && analysisData.status === 'not_started');

  useEffect(() => {
    if (contract && analysisNotStarted && !startAnalysis.isPending) {
      startAnalysis.mutate(contractId, {
        onSuccess: () => refetchAnalysis(),
      });
    }
  }, [contract?.contract_id]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleBindWorkflow = async () => {
    try {
      const result = await bindWorkflow.mutateAsync(contractId);
      addToast(result.status === 'bound' ? 'Договор привязан к workflow' : 'Уже привязан к workflow');
    } catch {
      addToast('Ошибка привязки к workflow', 'error');
    }
  };

  const handleSyncDeadlines = async () => {
    try {
      const result = await syncDeadlines.mutateAsync(contractId);
      addToast(`Создано дедлайнов: ${result.created}`);
    } catch {
      addToast('Ошибка синхронизации дедлайнов', 'error');
    }
  };

  const handleValidateParties = async () => {
    try {
      const result = await validateParties.mutateAsync(contractId);
      setValidationResult(result.issues);
      if (result.issues.length === 0) {
        addToast('Проверка пройдена: все стороны корректны');
      }
    } catch {
      addToast('Ошибка проверки сторон', 'error');
    }
  };

  const handleStartAnalysis = async () => {
    try {
      await startAnalysis.mutateAsync(contractId);
      await refetchAnalysis();
      addToast('ИИ-анализ выполнен');
    } catch {
      addToast('Ошибка запуска ИИ-анализа', 'error');
    }
  };

  const handleSendTo1C = async () => {
    try {
      const result = await sendTo1C.mutateAsync(contractId);
      addToast(result.message || 'Договор поставлен в очередь на отправку в 1С');
    } catch {
      addToast('Ошибка отправки в 1С', 'error');
    }
  };

  const formatCurrency = (value?: number) =>
    value
      ? new Intl.NumberFormat('ru-RU', { style: 'currency', currency: contract?.currency || 'RUB' }).format(value)
      : '—';

  // Состояние загрузки — скелетоны
  if (isLoading) {
    return (
      <div>
        <div className="flex items-center gap-4 mb-8">
          <Skeleton className="w-9 h-9" />
          <div className="flex-1">
            <Skeleton className="h-7 w-48 mb-2" />
            <Skeleton className="h-4 w-64" />
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Skeleton className="h-64 w-full" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
          <div className="space-y-6">
            <Skeleton className="h-48 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (!contract) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <p className="text-[#64748B] mb-4">Договор не найден</p>
        <Button onClick={() => navigate('/contracts')}>Назад к списку</Button>
      </div>
    );
  }

  const is1cStatus = contract.integration_1c_status || 'not_sent';
  const eisStatus  = contract.eis_status || 'not_sent';

  return (
    <div>
      {/* Toast-уведомления */}
      <div className="fixed top-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map(t => <Toast key={t.id} msg={t.msg} type={t.type} />)}
      </div>

      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <button
          onClick={() => navigate('/contracts')}
          className="p-2 rounded-lg hover:bg-gray-100 text-[#64748B] transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-bold text-[#1E293B]">{contract.contract_no}</h1>
            <StatusBadge status={contract.status_code} />
            <SourceBadge source={contract.source_code} />
          </div>
          <p className="text-[#64748B] mt-1">{contract.title}</p>
        </div>
      </div>

      {/* Валидация сторон — результат */}
      {validationResult && validationResult.length > 0 && (
        <div className="mb-6 p-4 rounded-lg border bg-[#FEF2F2] border-[#EF4444] text-[#EF4444]">
          <p className="font-medium mb-2">Обнаружены проблемы со сторонами:</p>
          <ul className="list-disc list-inside text-sm space-y-1">
            {validationResult.map((issue, i) => <li key={i}>{issue}</li>)}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ── Левая колонка (2/3) ── */}
        <div className="lg:col-span-2 space-y-6">

          {/* Основная информация */}
          <Card>
            <CardHeader title="Основная информация" />
            <CardContent>
              <dl className="grid grid-cols-2 gap-x-6 gap-y-4">
                <div>
                  <dt className="text-sm text-[#64748B]">Тип договора</dt>
                  <dd className="text-sm font-medium text-[#1E293B] mt-1">{contract.type_code || '—'}</dd>
                </div>
                <div>
                  <dt className="text-sm text-[#64748B]">Сумма</dt>
                  <dd className="text-sm font-medium text-[#1E293B] mt-1">{formatCurrency(contract.amount_total)}</dd>
                </div>
                <div>
                  <dt className="text-sm text-[#64748B]">Дата подписания</dt>
                  <dd className="text-sm font-medium text-[#1E293B] mt-1">{contract.sign_date || '—'}</dd>
                </div>
                <div>
                  <dt className="text-sm text-[#64748B]">Дата начала</dt>
                  <dd className="text-sm font-medium text-[#1E293B] mt-1">{contract.start_date || '—'}</dd>
                </div>
                <div>
                  <dt className="text-sm text-[#64748B]">Источник</dt>
                  <dd className="mt-1"><SourceBadge source={contract.source_code} /></dd>
                </div>
                <div>
                  <dt className="text-sm text-[#64748B]">Создан</dt>
                  <dd className="text-sm font-medium text-[#1E293B] mt-1">{contract.created_at.slice(0, 10)}</dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          {/* Риски и отклонения */}
          <Card>
            <CardHeader title="Риски и отклонения" />
            <CardContent>
              {contract.risks_cnt === 0 && contract.deviations_cnt === 0 ? (
                <p className="text-sm text-[#64748B]">Нарушений не обнаружено</p>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center justify-between py-2">
                    <span className="text-sm text-[#64748B]">Нерешённых рисков</span>
                    <Badge variant={contract.has_critical_risk ? 'danger' : 'warning'}>
                      {contract.risks_cnt ?? 0}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between py-2">
                    <span className="text-sm text-[#64748B]">Отклонений от шаблона</span>
                    <Badge variant="info">{contract.deviations_cnt ?? 0}</Badge>
                  </div>
                  {contract.has_critical_risk && (
                    <div className="p-3 bg-[#FEF2F2] rounded-lg">
                      <p className="text-sm text-[#EF4444] font-medium">
                        ⚠️ Обнаружены критические риски — требуется проверка специалистом
                      </p>
                    </div>
                  )}
                  <div className="pt-2">
                    <span className={`text-xs px-2 py-1 rounded-full font-medium
                      ${contract.risks_cnt === 0 && contract.deviations_cnt === 0
                        ? 'bg-[#ECFDF5] text-[#10B981]'
                        : 'bg-[#FFFBEB] text-[#F59E0B]'}`}>
                      {contract.risks_cnt === 0 && contract.deviations_cnt === 0
                        ? 'Проверено'
                        : 'Требует проверки'}
                    </span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Дедлайны */}
          <Card>
            <CardHeader title="Дедлайны" />
            <CardContent>
              {!contract.performance_due && !contract.payment_due && !contract.end_date ? (
                <p className="text-sm text-[#64748B]">Сроки не указаны</p>
              ) : (
                <div>
                  {contract.performance_due && (
                    <DeadlineRow label="Срок исполнения обязательств" date={contract.performance_due} />
                  )}
                  {contract.payment_due && (
                    <DeadlineRow label="Срок оплаты" date={contract.payment_due} />
                  )}
                  {contract.end_date && (
                    <DeadlineRow label="Дата окончания договора" date={contract.end_date} />
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* ИИ-анализ */}
          <Card>
            <CardHeader
              title="Анализ договора (ИИ)"
              action={
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={handleStartAnalysis}
                  loading={startAnalysis.isPending}
                >
                  <Brain className="w-3.5 h-3.5" />
                  {analysis ? 'Повторный анализ' : 'Запустить анализ'}
                </Button>
              }
            />
            <CardContent>
              {startAnalysis.isPending ? (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-16 w-full" />
                </div>
              ) : analysis ? (
                <AIAnalysisBlock analysis={analysis} />
              ) : (
                <p className="text-sm text-[#64748B]">ИИ-анализ не выполнялся</p>
              )}
              <p className="text-xs text-[#94A3B8] mt-4 pt-3 border-t border-[#E2E8F0]">
                Результаты ИИ-анализа носят рекомендательный характер и требуют проверки специалистом
              </p>
            </CardContent>
          </Card>

          {/* Таймлайн */}
          <Card>
            <CardHeader title="История изменений" />
            <CardContent>
              {timelineLoading ? (
                <div className="space-y-4">
                  {[1, 2, 3].map(i => (
                    <div key={i} className="flex gap-4">
                      <Skeleton className="w-3 h-3 rounded-full mt-1.5 shrink-0" />
                      <div className="flex-1 space-y-1">
                        <Skeleton className="h-4 w-48" />
                        <Skeleton className="h-3 w-32" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : !timeline?.length ? (
                <p className="text-sm text-[#64748B]">История изменений отсутствует</p>
              ) : (
                <TimelineList entries={timeline} />
              )}
            </CardContent>
          </Card>
        </div>

        {/* ── Правая колонка (1/3) ── */}
        <div className="space-y-6">

          {/* Действия */}
          <Card>
            <CardHeader title="Действия" />
            <CardContent className="space-y-3">
              <Button
                onClick={handleSendTo1C}
                loading={sendTo1C.isPending}
                className="w-full justify-start"
                disabled={is1cStatus === 'sent' || is1cStatus === 'queued'}
              >
                <Send className="w-4 h-4" />
                {is1cStatus === 'sent' ? 'Отправлен в 1С' : is1cStatus === 'queued' ? 'В очереди на отправку' : 'Отправить в 1С'}
              </Button>
              <Button
                onClick={handleBindWorkflow}
                loading={bindWorkflow.isPending}
                className="w-full justify-start"
                variant="secondary"
              >
                <Play className="w-4 h-4" />
                Запустить согласование
              </Button>
              <Button
                onClick={handleSyncDeadlines}
                loading={syncDeadlines.isPending}
                className="w-full justify-start"
                variant="secondary"
              >
                <RefreshCw className="w-4 h-4" />
                Синхронизировать дедлайны
              </Button>
              <Button
                onClick={handleValidateParties}
                loading={validateParties.isPending}
                className="w-full justify-start"
                variant="secondary"
              >
                <UserCheck className="w-4 h-4" />
                Проверить стороны
              </Button>
            </CardContent>
          </Card>

          {/* Интеграция */}
          <Card>
            <CardHeader title="Интеграция" />
            <CardContent className="space-y-4">
              <div>
                <p className="text-xs text-[#94A3B8] uppercase tracking-wide mb-1.5">1С</p>
                <IntegrationStatusDot status={is1cStatus} />
                {contract.integration_1c_error && (
                  <p className="text-xs text-[#EF4444] mt-1">
                    Ошибка: {contract.integration_1c_error}
                  </p>
                )}
                {contract.integration_1c_sent_at && is1cStatus === 'sent' && (
                  <p className="text-xs text-[#94A3B8] mt-1">
                    {contract.integration_1c_sent_at.slice(0, 10)}
                  </p>
                )}
              </div>

              <div className="border-t border-[#E2E8F0] pt-4">
                <p className="text-xs text-[#94A3B8] uppercase tracking-wide mb-1.5">ЕИС</p>
                <IntegrationStatusDot status={eisStatus} />
                {contract.eis_updated_at && eisStatus !== 'not_sent' && (
                  <p className="text-xs text-[#94A3B8] mt-1">
                    {contract.eis_updated_at.slice(0, 10)}
                  </p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Гарантия */}
          <Card>
            <CardHeader title="Банковская гарантия" />
            <CardContent>
              {contract.has_active_guarantee ? (
                <div className="flex items-center gap-2">
                  <span className="text-green-500 text-lg">🟢</span>
                  <span className="text-sm font-medium text-[#10B981]">Активная гарантия есть</span>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <span className="text-lg">🟡</span>
                  <span className="text-sm text-[#F59E0B]">Без активной гарантии</span>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
