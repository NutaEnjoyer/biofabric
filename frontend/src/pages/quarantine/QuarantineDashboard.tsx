import { useState } from 'react';
import {
  PlusCircle, Upload, Download, FlaskConical,
  ArrowDownCircle, ArrowUpCircle, RefreshCw, CheckCircle,
} from 'lucide-react';
import {
  Card, CardHeader, CardContent, Button, Input, Modal, Select, MetricCard, Table, Badge,
} from '../../components/ui';
import {
  useMonthlySummary, useCreateOperation, useImportCsv, useSpecies,
  useDashboard, useDynamics, useVivariumGroups, useHistory,
  useAgeCategories, useMassBins, useGroups, useConfirmOperation,
} from '../../hooks/useQuarantine';
import { downloadCsv } from '../../api/quarantine';
import type {
  OperationCreate, OpType, DirectionCode, MonthlySummaryRow, HistoryEntry,
} from '../../types/quarantine';

type Tab = 'summary' | 'dynamics' | 'history' | 'vivarium';

const currentPeriod = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
};

const sixMonthsAgo = () => {
  const d = new Date();
  d.setMonth(d.getMonth() - 5);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
};

const OP_TYPE_OPTIONS = [
  { value: 'opening_balance',   label: 'Начальный остаток' },
  { value: 'intake',            label: 'Приход' },
  { value: 'withdrawal',        label: 'Расход' },
  { value: 'issue_for_control', label: 'Выдача на контроль' },
  { value: 'movement',          label: 'Перемещение' },
  { value: 'adjustment',        label: 'Корректировка' },
];

const DIRECTION_OPTIONS = [
  { value: 'subsidiary', label: 'Подсобное хозяйство' },
  { value: 'vivarium',   label: 'Виварий' },
];

const SEX_OPTIONS = [
  { value: '',  label: 'Не указан' },
  { value: 'M', label: 'Самец' },
  { value: 'F', label: 'Самка' },
  { value: 'U', label: 'Неизвестно' },
];

const GROUP_BY_OPTIONS = [
  { value: 'direction', label: 'По направлению' },
  { value: 'species',   label: 'По виду' },
  { value: 'total',     label: 'Итого' },
];

function directionLabel(code: DirectionCode) {
  return code === 'subsidiary' ? 'Подсобное хоз-во' : 'Виварий';
}

function opTypeLabel(code: string) {
  const map: Record<string, string> = {
    opening_balance:  'Начальный остаток',
    intake:           'Приход',
    withdrawal:       'Расход',
    issue_for_control:'Выдача на контроль',
    movement_in:      'Перемещение (вход)',
    movement_out:     'Перемещение (выход)',
    adjustment:       'Корректировка',
  };
  return map[code] ?? code;
}

function statusBadge(status: string) {
  if (status === 'in_process') return <Badge variant="warning">В обработке</Badge>;
  if (status === 'current')    return <Badge variant="success">Актуальная</Badge>;
  return <Badge variant="default">Архив</Badge>;
}

// Простой SVG-барчарт без внешних зависимостей
function BarChart({ data }: { data: { label: string; value: number; color?: string }[] }) {
  const max = Math.max(...data.map((d) => d.value), 1);
  const BAR_H = 180;
  const BAR_W = Math.max(28, Math.floor(560 / Math.max(data.length, 1)) - 8);
  const GAP = 8;
  const total_w = data.length * (BAR_W + GAP);

  return (
    <div className="overflow-x-auto">
      <svg width={Math.max(total_w, 200)} height={BAR_H + 40} className="block">
        {data.map((d, i) => {
          const barHeight = Math.max(2, Math.round((d.value / max) * BAR_H));
          const x = i * (BAR_W + GAP);
          const y = BAR_H - barHeight;
          const color = d.color ?? '#2563EB';
          return (
            <g key={i}>
              <rect x={x} y={y} width={BAR_W} height={barHeight} rx={3} fill={color} opacity={0.85} />
              <text x={x + BAR_W / 2} y={BAR_H + 16} textAnchor="middle" fontSize={10} fill="#64748B">
                {d.label.length > 7 ? d.label.slice(5) : d.label}
              </text>
              <text x={x + BAR_W / 2} y={y - 4} textAnchor="middle" fontSize={10} fill="#1E293B" fontWeight="600">
                {d.value}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

const emptyForm = (): OperationCreate => ({
  date: new Date().toISOString().slice(0, 10),
  period_month: currentPeriod(),
  op_type: 'intake',
  species_code: '',
  direction_code: 'vivarium',
  quantity: 1,
});

export function QuarantineDashboard() {
  const [tab, setTab] = useState<Tab>('summary');
  const [period, setPeriod] = useState(currentPeriod());
  const [modalOpen, setModalOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [form, setForm] = useState<OperationCreate>(emptyForm());
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Dynamics controls
  const [dynFrom, setDynFrom] = useState(sixMonthsAgo());
  const [dynTo, setDynTo] = useState(currentPeriod());
  const [dynGroupBy, setDynGroupBy] = useState<'direction' | 'species' | 'total'>('direction');

  // History controls
  const [histSpecies, setHistSpecies] = useState('');
  const [histDirection, setHistDirection] = useState<DirectionCode>('vivarium');

  // Data queries
  const { data: summary = [],       isLoading: summaryLoading } = useMonthlySummary(period);
  const { data: dashboard }                                      = useDashboard(period);
  const { data: dynamics = [] }                                  = useDynamics(dynFrom, dynTo, dynGroupBy);
  const { data: historyEntries = [], isLoading: histLoading }   = useHistory(histSpecies, histDirection);
  const { data: vivariumGroups = [] }                            = useVivariumGroups(period);
  const { data: speciesList = [] }                               = useSpecies();
  const { data: groups = [] }                                    = useGroups();
  const { data: ageCats = [] }                                   = useAgeCategories(form.species_code);
  const { data: massBins = [] }                                  = useMassBins(form.species_code);

  const createOp   = useCreateOperation();
  const confirmOp  = useConfirmOperation();
  const importMut  = useImportCsv();

  const speciesOptions  = speciesList.map((s) => ({ value: s.code, label: s.name }));
  // Группы — только те, что подходят к выбранному направлению
  const groupOptions = groups
    .filter((g) => !form.direction_code || g.direction_code === form.direction_code)
    .map((g) => ({ value: g.name, label: g.name }));
  const ageCatOptions  = ageCats.map((c) => ({ value: c.name, label: c.name }));
  const massBinOptions = massBins.map((b) => ({ value: b.name, label: b.name }));
  const selectedSpecies = speciesList.find((s) => s.code === form.species_code);

  const flash = (msg: string, isError = false) => {
    if (isError) setErrorMsg(msg); else setSuccessMsg(msg);
    setTimeout(() => { setSuccessMsg(null); setErrorMsg(null); }, 4000);
  };

  const handleSubmit = async () => {
    if (!form.species_code) { flash('Выберите вид животного', true); return; }
    try {
      await createOp.mutateAsync(form);
      setModalOpen(false);
      setForm(emptyForm());
      flash('Операция создана (статус: В обработке — ожидает подтверждения руководителем)');
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      flash(err.response?.data?.detail ?? 'Ошибка при создании', true);
    }
  };

  const handleConfirm = async (entryId: number) => {
    try {
      await confirmOp.mutateAsync(entryId);
      flash('Запись подтверждена — статус изменён на «Актуальная»');
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      flash(err.response?.data?.detail ?? 'Ошибка подтверждения', true);
    }
  };

  const handleImport = async () => {
    if (!csvFile) return;
    try {
      const result = await importMut.mutateAsync(csvFile);
      setImportOpen(false);
      setCsvFile(null);
      flash(result.message || 'Импорт выполнен');
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      flash(err.response?.data?.detail ?? 'Ошибка импорта', true);
    }
  };

  // ── Columns ──────────────────────────────────────────────────────────────

  const summaryColumns = [
    {
      key: 'species_code', header: 'Вид',
      render: (r: MonthlySummaryRow) => <span className="font-medium">{r.species_code}</span>,
    },
    {
      key: 'direction_code', header: 'Направление',
      render: (r: MonthlySummaryRow) => (
        <Badge variant={r.direction_code === 'vivarium' ? 'info' : 'default'}>
          {directionLabel(r.direction_code)}
        </Badge>
      ),
    },
    {
      key: 'intake', header: 'Приход', className: 'text-right',
      render: (r: MonthlySummaryRow) => <span className="text-[#10B981]">+{r.intake}</span>,
    },
    {
      key: 'withdrawal', header: 'Расход', className: 'text-right',
      render: (r: MonthlySummaryRow) => <span className="text-[#EF4444]">-{r.withdrawal}</span>,
    },
    {
      key: 'issue_for_control', header: 'На контроль', className: 'text-right',
      render: (r: MonthlySummaryRow) => r.issue_for_control,
    },
    {
      key: 'adjustment', header: 'Корр.', className: 'text-right',
      render: (r: MonthlySummaryRow) => (
        <span className={r.adjustment !== 0 ? 'text-[#F59E0B]' : ''}>{r.adjustment}</span>
      ),
    },
    {
      key: 'closing_balance', header: 'Остаток кон.', className: 'text-right',
      render: (r: MonthlySummaryRow) => <span className="font-semibold">{r.closing_balance}</span>,
    },
  ];

  const historyColumns = [
    {
      key: 'entry_date', header: 'Дата',
      render: (r: HistoryEntry) => <span className="text-sm">{r.entry_date}</span>,
    },
    {
      key: 'entry_type', header: 'Тип операции',
      render: (r: HistoryEntry) => <span className="text-sm">{opTypeLabel(r.entry_type)}</span>,
    },
    {
      key: 'quantity', header: 'Кол-во', className: 'text-right',
      render: (r: HistoryEntry) => <span className="font-medium">{r.quantity}</span>,
    },
    {
      key: 'group_name', header: 'Группа',
      render: (r: HistoryEntry) => r.group_name ?? '—',
    },
    {
      key: 'status_code', header: 'Статус',
      render: (r: HistoryEntry) => statusBadge(r.status_code),
    },
    {
      key: 'actions', header: '',
      render: (r: HistoryEntry) =>
        r.status_code === 'in_process' ? (
          <button
            onClick={() => handleConfirm(r.entry_id)}
            className="flex items-center gap-1 text-xs text-[#2563EB] hover:text-[#1D4ED8] font-medium"
          >
            <CheckCircle className="w-4 h-4" />
            Подтвердить
          </button>
        ) : null,
    },
  ];

  const COLORS: Record<string, string> = {
    vivarium:   '#2563EB',
    subsidiary: '#10B981',
    total:      '#8B5CF6',
  };

  const dynamicsChartData = dynamics.map((d) => ({
    label: `${d.period_month}·${d.group_key}`,
    value: d.balance,
    color: COLORS[d.group_key] ?? '#64748B',
  }));

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-[#1E293B]">Карантин животных</h1>
          <p className="text-[#64748B] mt-1">Учёт движения поголовья по периодам</p>
        </div>
        <div className="flex gap-3">
          <Button variant="secondary" onClick={() => downloadCsv(period)}>
            <Download className="w-4 h-4" />
            Экспорт CSV
          </Button>
          <Button variant="secondary" onClick={() => setImportOpen(true)}>
            <Upload className="w-4 h-4" />
            Импорт CSV
          </Button>
          <Button onClick={() => setModalOpen(true)}>
            <PlusCircle className="w-4 h-4" />
            Новая операция
          </Button>
        </div>
      </div>

      {/* Alerts */}
      {successMsg && (
        <div className="mb-6 p-4 bg-[#ECFDF5] border border-[#10B981] rounded-lg text-[#10B981]">
          {successMsg}
        </div>
      )}
      {errorMsg && (
        <div className="mb-6 p-4 bg-[#FEF2F2] border border-[#EF4444] rounded-lg text-[#EF4444]">
          {errorMsg}
        </div>
      )}

      {/* Period picker */}
      <div className="flex items-center gap-3 mb-6">
        <span className="text-sm text-[#64748B]">Период:</span>
        <Input type="month" value={period} onChange={(e) => setPeriod(e.target.value)} className="w-40" />
        <button
          onClick={() => setPeriod(currentPeriod())}
          className="flex items-center gap-1 text-sm text-[#64748B] hover:text-[#1E293B] transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Текущий
        </button>
      </div>

      {/* Dashboard metrics */}
      {dashboard && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <MetricCard
            title="Всего поголовье"
            value={dashboard.total.current}
            subtitle={`${dashboard.total.delta > 0 ? '+' : ''}${dashboard.total.delta} к пред. месяцу`}
            icon={FlaskConical}
            iconColor="text-[#2563EB]"
            iconBg="bg-blue-50"
          />
          {dashboard.by_direction.map((d) => (
            <MetricCard
              key={d.direction_code}
              title={directionLabel(d.direction_code)}
              value={d.current}
              subtitle={`${d.delta > 0 ? '+' : ''}${d.delta} к пред. месяцу`}
              icon={d.trend === 'up' ? ArrowDownCircle : d.trend === 'down' ? ArrowUpCircle : FlaskConical}
              iconColor={
                d.trend === 'up' ? 'text-[#10B981]' : d.trend === 'down' ? 'text-[#EF4444]' : 'text-[#94A3B8]'
              }
              iconBg={
                d.trend === 'up' ? 'bg-green-50' : d.trend === 'down' ? 'bg-red-50' : 'bg-slate-50'
              }
            />
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-[#E2E8F0] mb-6">
        {(
          [
            { key: 'summary',  label: 'Сводка' },
            { key: 'dynamics', label: 'Динамика' },
            { key: 'history',  label: 'История' },
            { key: 'vivarium', label: 'Виварий' },
          ] as { key: Tab; label: string }[]
        ).map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key
                ? 'border-[#2563EB] text-[#2563EB]'
                : 'border-transparent text-[#64748B] hover:text-[#1E293B]'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Сводка ──────────────────────────────────────────────────────────── */}
      {tab === 'summary' && (
        <Card>
          <CardHeader title="Свод за период" description={`${period} · ${summary.length} строк`} />
          <CardContent className="p-0">
            <Table
              columns={summaryColumns}
              data={summary}
              keyExtractor={(r) => `${r.species_code}-${r.direction_code}`}
              loading={summaryLoading}
              emptyMessage="Нет данных за выбранный период"
            />
          </CardContent>
        </Card>
      )}

      {/* ── Динамика ────────────────────────────────────────────────────────── */}
      {tab === 'dynamics' && (
        <Card>
          <CardHeader title="Динамика численности" description="Остаток по месяцам" />
          <CardContent>
            <div className="flex flex-wrap gap-4 mb-6">
              <div>
                <label className="block text-xs text-[#64748B] mb-1">Начало</label>
                <Input type="month" value={dynFrom} onChange={(e) => setDynFrom(e.target.value)} className="w-36" />
              </div>
              <div>
                <label className="block text-xs text-[#64748B] mb-1">Конец</label>
                <Input type="month" value={dynTo} onChange={(e) => setDynTo(e.target.value)} className="w-36" />
              </div>
              <div>
                <label className="block text-xs text-[#64748B] mb-1">Группировка</label>
                <Select
                  options={GROUP_BY_OPTIONS}
                  value={dynGroupBy}
                  onChange={(e) => setDynGroupBy(e.target.value as typeof dynGroupBy)}
                  className="w-48"
                />
              </div>
            </div>
            {dynamics.length > 0 ? (
              <>
                <BarChart data={dynamicsChartData} />
                <div className="flex gap-4 mt-4 flex-wrap">
                  {[...new Set(dynamics.map((d) => d.group_key))].map((key) => (
                    <span key={key} className="flex items-center gap-1 text-xs text-[#64748B]">
                      <span
                        className="inline-block w-3 h-3 rounded-sm"
                        style={{ background: COLORS[key] ?? '#64748B' }}
                      />
                      {key === 'vivarium' ? 'Виварий' : key === 'subsidiary' ? 'Подсобное хоз-во' : key}
                    </span>
                  ))}
                </div>
              </>
            ) : (
              <p className="text-sm text-[#94A3B8] py-8 text-center">Нет данных за выбранный период</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* ── История ─────────────────────────────────────────────────────────── */}
      {tab === 'history' && (
        <Card>
          <CardHeader title="История операций" description="Таймлайн по виду и направлению" />
          <CardContent>
            <div className="flex flex-wrap gap-4 mb-6">
              <div>
                <label className="block text-xs text-[#64748B] mb-1">Вид *</label>
                <Select
                  options={[{ value: '', label: 'Выберите вид...' }, ...speciesOptions]}
                  value={histSpecies}
                  onChange={(e) => setHistSpecies(e.target.value)}
                  className="w-48"
                />
              </div>
              <div>
                <label className="block text-xs text-[#64748B] mb-1">Направление *</label>
                <Select
                  options={DIRECTION_OPTIONS}
                  value={histDirection}
                  onChange={(e) => setHistDirection(e.target.value as DirectionCode)}
                  className="w-48"
                />
              </div>
            </div>
            <Table
              columns={historyColumns}
              data={historyEntries}
              keyExtractor={(r) => String(r.entry_id)}
              loading={histLoading}
              emptyMessage={
                histSpecies ? 'Нет записей по выбранным фильтрам' : 'Выберите вид для просмотра истории'
              }
            />
          </CardContent>
        </Card>
      )}

      {/* ── Виварий ─────────────────────────────────────────────────────────── */}
      {tab === 'vivarium' && (
        <div className="space-y-4">
          {vivariumGroups.length === 0 ? (
            <Card>
              <CardContent>
                <p className="text-sm text-[#94A3B8] py-8 text-center">
                  Нет активных групп вивария за {period}
                </p>
              </CardContent>
            </Card>
          ) : (
            vivariumGroups.map((g) => (
              <Card key={g.group_id}>
                <CardHeader
                  title={g.group_name}
                  description={`${g.species.reduce((s, x) => s + x.balance, 0)} животных`}
                />
                <CardContent>
                  <div className="flex flex-wrap gap-3">
                    {g.species.map((sp) => (
                      <div
                        key={sp.species_code}
                        className="flex items-center gap-2 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg px-4 py-3"
                      >
                        <FlaskConical className="w-4 h-4 text-[#2563EB]" />
                        <div>
                          <p className="text-sm font-medium text-[#1E293B]">{sp.species_name}</p>
                          <p className="text-xs text-[#64748B]">{sp.balance} ос.</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}

      {/* ── Modal: Новая операция ────────────────────────────────────────────── */}
      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Новая операция" size="lg">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-[#64748B] mb-1">Дата *</label>
            <Input
              type="date"
              value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm text-[#64748B] mb-1">Период *</label>
            <Input
              type="month"
              value={form.period_month}
              onChange={(e) => setForm({ ...form, period_month: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm text-[#64748B] mb-1">Тип операции *</label>
            <Select
              options={OP_TYPE_OPTIONS}
              value={form.op_type}
              onChange={(e) => setForm({ ...form, op_type: e.target.value as OpType })}
            />
          </div>
          <div>
            <label className="block text-sm text-[#64748B] mb-1">Направление *</label>
            <Select
              options={DIRECTION_OPTIONS}
              value={form.direction_code}
              onChange={(e) => setForm({
                ...form,
                direction_code: e.target.value as DirectionCode,
                group_code: undefined,
              })}
            />
          </div>
          <div>
            <label className="block text-sm text-[#64748B] mb-1">Вид *</label>
            <Select
              options={[{ value: '', label: 'Выберите вид...' }, ...speciesOptions]}
              value={form.species_code}
              onChange={(e) => setForm({
                ...form,
                species_code: e.target.value,
                age_bin_code: undefined,
                mass_bin_code: undefined,
              })}
            />
          </div>
          <div>
            <label className="block text-sm text-[#64748B] mb-1">Количество *</label>
            <Input
              type="number"
              min={1}
              value={form.quantity}
              onChange={(e) => setForm({ ...form, quantity: Number(e.target.value) })}
            />
          </div>
          <div>
            <label className="block text-sm text-[#64748B] mb-1">Пол</label>
            <Select
              options={SEX_OPTIONS}
              value={form.sex ?? ''}
              onChange={(e) => setForm({ ...form, sex: (e.target.value as OperationCreate['sex']) || undefined })}
            />
          </div>

          {/* Возрастная категория — если вид поддерживает */}
          {selectedSpecies?.has_age_categories && ageCatOptions.length > 0 && (
            <div>
              <label className="block text-sm text-[#64748B] mb-1">Возрастная категория</label>
              <Select
                options={[{ value: '', label: 'Не указана' }, ...ageCatOptions]}
                value={form.age_bin_code ?? ''}
                onChange={(e) => setForm({ ...form, age_bin_code: e.target.value || undefined })}
              />
            </div>
          )}

          {/* Весовая категория — если вид поддерживает */}
          {selectedSpecies?.has_mass_bins && massBinOptions.length > 0 && (
            <div>
              <label className="block text-sm text-[#64748B] mb-1">Весовая категория</label>
              <Select
                options={[{ value: '', label: 'Не указана' }, ...massBinOptions]}
                value={form.mass_bin_code ?? ''}
                onChange={(e) => setForm({ ...form, mass_bin_code: e.target.value || undefined })}
              />
            </div>
          )}

          {/* Группа — для не-перемещений */}
          {form.op_type !== 'movement' && groupOptions.length > 0 && (
            <div>
              <label className="block text-sm text-[#64748B] mb-1">Группа</label>
              <Select
                options={[{ value: '', label: 'Не указана' }, ...groupOptions]}
                value={form.group_code ?? ''}
                onChange={(e) => setForm({ ...form, group_code: e.target.value || undefined })}
              />
            </div>
          )}

          {/* Перемещение: src/dst */}
          {form.op_type === 'movement' && (
            <>
              <div>
                <label className="block text-sm text-[#64748B] mb-1">Источник (группа)</label>
                <Select
                  options={[{ value: '', label: 'Выберите...' }, ...groupOptions]}
                  value={form.src_group_code ?? ''}
                  onChange={(e) => setForm({ ...form, src_group_code: e.target.value || undefined })}
                />
              </div>
              <div>
                <label className="block text-sm text-[#64748B] mb-1">Приёмник (группа)</label>
                <Select
                  options={[{ value: '', label: 'Выберите...' }, ...groupOptions]}
                  value={form.dst_group_code ?? ''}
                  onChange={(e) => setForm({ ...form, dst_group_code: e.target.value || undefined })}
                />
              </div>
            </>
          )}

          {/* Выдача на контроль */}
          {form.op_type === 'issue_for_control' && (
            <div className="col-span-2">
              <label className="block text-sm text-[#64748B] mb-1">Назначение *</label>
              <Input
                placeholder="Цель выдачи на контроль"
                value={form.purpose_text ?? ''}
                onChange={(e) => setForm({ ...form, purpose_text: e.target.value })}
              />
            </div>
          )}

          {/* Корректировка */}
          {form.op_type === 'adjustment' && (
            <>
              <div className="col-span-2">
                <label className="block text-sm text-[#64748B] mb-1">Причина *</label>
                <Input
                  placeholder="Укажите причину корректировки"
                  value={form.reason ?? ''}
                  onChange={(e) => setForm({ ...form, reason: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm text-[#64748B] mb-1">Корректируемый период</label>
                <Input
                  type="month"
                  value={form.adjusts_period ?? ''}
                  onChange={(e) => setForm({ ...form, adjusts_period: e.target.value || undefined })}
                />
              </div>
            </>
          )}
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <Button variant="secondary" onClick={() => { setModalOpen(false); setForm(emptyForm()); }}>
            Отмена
          </Button>
          <Button onClick={handleSubmit} loading={createOp.isPending}>
            Создать операцию
          </Button>
        </div>
      </Modal>

      {/* ── Modal: Импорт CSV ────────────────────────────────────────────────── */}
      <Modal isOpen={importOpen} onClose={() => setImportOpen(false)} title="Импорт из CSV" size="sm">
        <p className="text-sm text-[#64748B] mb-4">
          Обязательные колонки:{' '}
          <code className="bg-gray-100 px-1 rounded text-xs">
            date, period_month, op_type, species_code, direction_code, quantity
          </code>
        </p>
        <input
          type="file"
          accept=".csv"
          className="block w-full text-sm text-[#64748B] file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-[#2563EB] hover:file:bg-blue-100"
          onChange={(e) => setCsvFile(e.target.files?.[0] ?? null)}
        />
        <div className="flex justify-end gap-3 mt-6">
          <Button variant="secondary" onClick={() => setImportOpen(false)}>Отмена</Button>
          <Button onClick={handleImport} loading={importMut.isPending} disabled={!csvFile}>
            Загрузить
          </Button>
        </div>
      </Modal>
    </div>
  );
}
