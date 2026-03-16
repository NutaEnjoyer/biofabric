import { useState } from 'react';
import { Sparkles, BrainCircuit, ListChecks } from 'lucide-react';
import { Card, CardHeader, CardContent, Table, Button, Input, Badge } from '../../components/ui';
import {
  useAIGeneratePlan, useAIGenerateIdeas, usePlanJobs, useCreatePlanJob,
} from '../../hooks/useMarketing';
import type { PlanJob, PlanJobStatus } from '../../types/marketing';

const jobStatusConfig: Record<PlanJobStatus, { label: string; variant: 'default' | 'warning' | 'success' | 'danger' }> = {
  pending: { label: 'В очереди', variant: 'default' },
  running: { label: 'Выполняется', variant: 'warning' },
  done:    { label: 'Готово',     variant: 'success' },
  failed:  { label: 'Ошибка',     variant: 'danger' },
};

export function MarketingAI() {
  // Генерация по промту
  const [prompt, setPrompt] = useState('');
  const [promptResult, setPromptResult] = useState<number[] | null>(null);
  const aiPlan = useAIGeneratePlan();

  // Генерация из источников
  const [ideasResult, setIdeasResult] = useState<number[] | null>(null);
  const aiIdeas = useAIGenerateIdeas();

  // Plan jobs
  const { data: jobs = [], isLoading: jobsLoading } = usePlanJobs();
  const createJob = useCreatePlanJob();
  const [jobForm, setJobForm] = useState({
    period_start: '',
    period_end: '',
    audience: '',
    goals: '',
    tone: '',
  });
  const [jobResult, setJobResult] = useState<{ job_id: number; post_count: number } | null>(null);

  const handlePromptPlan = async () => {
    if (!prompt.trim()) return;
    const res = await aiPlan.mutateAsync({ prompt });
    setPromptResult(res.created_post_ids);
    setTimeout(() => setPromptResult(null), 5000);
  };

  const handleIdeas = async () => {
    const res = await aiIdeas.mutateAsync({});
    setIdeasResult(res.created_post_ids);
    setTimeout(() => setIdeasResult(null), 5000);
  };

  const handleCreateJob = async () => {
    if (!jobForm.period_start || !jobForm.period_end) return;
    const res = await createJob.mutateAsync({
      period_start: jobForm.period_start,
      period_end: jobForm.period_end,
      audience: jobForm.audience || undefined,
      goals: jobForm.goals || undefined,
      tone: jobForm.tone || undefined,
    });
    setJobResult({ job_id: res.job_id, post_count: res.created_post_ids.length });
    setJobForm({ period_start: '', period_end: '', audience: '', goals: '', tone: '' });
    setTimeout(() => setJobResult(null), 5000);
  };

  const jobColumns = [
    { key: 'job_id', header: '№', render: (j: PlanJob) => `#${j.job_id}` },
    {
      key: 'period',
      header: 'Период',
      render: (j: PlanJob) => `${j.period_start} — ${j.period_end}`,
    },
    {
      key: 'audience',
      header: 'ЦА / Цели',
      render: (j: PlanJob) => (
        <span className="text-sm text-[#64748B]">
          {[j.audience, j.goals].filter(Boolean).join(' · ') || '—'}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Статус',
      render: (j: PlanJob) => {
        const cfg = jobStatusConfig[j.status] ?? { label: j.status, variant: 'default' };
        return <Badge variant={cfg.variant}>{cfg.label}</Badge>;
      },
    },
  ];

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-[#1E293B]">ИИ и планирование</h1>
        <p className="text-[#64748B] mt-1">Генерация контент-планов и идей</p>
      </div>

      {/* Дисклеймер ИИ — обязателен по ТЗ п.7 */}
      <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-3">
        <Sparkles className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-amber-800">Важно</p>
          <p className="text-sm text-amber-700 mt-0.5">
            Материалы, сформированные ИИ, подлежат обязательной проверке и утверждению.
            ИИ является инструментом подготовки и предложений — он не публикует и не утверждает контент.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Генерация по промту */}
        <Card>
          <CardHeader
            title="Генерация по промту"
            description="ИИ создаст 3 черновика постов без дат"
            action={<Sparkles className="w-5 h-5 text-[#8B5CF6]" />}
          />
          <CardContent className="space-y-4">
            {promptResult && (
              <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg text-purple-700 text-sm">
                Создано {promptResult.length} черновиков: #{promptResult.join(', #')}
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-[#374151] mb-1">Промт</label>
              <textarea
                className="w-full border border-[#E2E8F0] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB] min-h-[100px]"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Опишите тему, аудиторию и цель публикаций..."
              />
            </div>
            <Button
              className="w-full"
              onClick={handlePromptPlan}
              loading={aiPlan.isPending}
              disabled={!prompt.trim()}
            >
              <Sparkles className="w-4 h-4" />
              Сгенерировать черновики
            </Button>
          </CardContent>
        </Card>

        {/* Идеи из источников */}
        <Card>
          <CardHeader
            title="Идеи из источников"
            description="ИИ создаст идеи на основе материалов из whitelist-источников"
            action={<BrainCircuit className="w-5 h-5 text-[#10B981]" />}
          />
          <CardContent className="space-y-4">
            {ideasResult && (
              <div className="p-3 bg-[#ECFDF5] border border-[#10B981] rounded-lg text-[#10B981] text-sm">
                Создано {ideasResult.length} идей: #{ideasResult.join(', #')}
              </div>
            )}
            <p className="text-sm text-[#64748B]">
              Берёт материалы из всех источников whitelist (до 10 с каждого) и генерирует черновики-идеи в корзину.
            </p>
            <Button
              className="w-full"
              variant="secondary"
              onClick={handleIdeas}
              loading={aiIdeas.isPending}
            >
              <BrainCircuit className="w-4 h-4" />
              Создать идеи из источников
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Задания генерации (plan jobs) */}
      <Card>
        <CardHeader
          title="Задания на контент-план"
          description="Постановка задачи с периодом, ЦА и tone of voice"
          action={<ListChecks className="w-5 h-5 text-[#2563EB]" />}
        />
        <CardContent>
          {jobResult && (
            <div className="mb-4 p-3 bg-[#ECFDF5] border border-[#10B981] rounded-lg text-[#10B981] text-sm">
              Задание #{jobResult.job_id} выполнено — создано {jobResult.post_count} черновиков
            </div>
          )}

          {/* Форма создания */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
            <Input
              label="Период с"
              type="date"
              value={jobForm.period_start}
              onChange={(e) => setJobForm({ ...jobForm, period_start: e.target.value })}
            />
            <Input
              label="Период по"
              type="date"
              value={jobForm.period_end}
              onChange={(e) => setJobForm({ ...jobForm, period_end: e.target.value })}
            />
            <Input
              label="Целевая аудитория"
              value={jobForm.audience}
              onChange={(e) => setJobForm({ ...jobForm, audience: e.target.value })}
              placeholder="Специалисты отрасли"
            />
            <Input
              label="Цели публикаций"
              value={jobForm.goals}
              onChange={(e) => setJobForm({ ...jobForm, goals: e.target.value })}
              placeholder="Имиджевые, информационные"
            />
            <Input
              label="Tone of voice"
              value={jobForm.tone}
              onChange={(e) => setJobForm({ ...jobForm, tone: e.target.value })}
              placeholder="Профессиональный, дружелюбный"
            />
          </div>
          <div className="flex justify-end mb-6">
            <Button
              onClick={handleCreateJob}
              loading={createJob.isPending}
              disabled={!jobForm.period_start || !jobForm.period_end}
            >
              <Sparkles className="w-4 h-4" />
              Сформировать план
            </Button>
          </div>

          {/* История заданий */}
          <Table
            columns={jobColumns}
            data={jobs}
            keyExtractor={(j) => j.job_id}
            loading={jobsLoading}
            emptyMessage="Заданий ещё не было"
          />
        </CardContent>
      </Card>
    </div>
  );
}
