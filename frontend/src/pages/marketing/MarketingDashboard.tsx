import { useState } from 'react';
import { CalendarDays, LayoutList, AlertCircle, CheckCircle, TriangleAlert } from 'lucide-react';
import { MetricCard, Card, CardHeader, CardContent, Table, Button } from '../../components/ui';
import {
  useAnalyticsByChannel,
  useAnalyticsByTopic,
  useAnalyticsGaps,
  useAnalyticsDensity,
  useAnalyticsWarnings,
  useNotifyUpcoming,
} from '../../hooks/useMarketing';
import type { DistributionRow, GapRow, ContentWarning } from '../../types/marketing';

// Баннер предупреждения (ТЗ п.4.3)
function WarningBanner({ warning }: { warning: ContentWarning }) {
  return (
    <div className="flex items-start gap-3 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm">
      <TriangleAlert className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
      <span className="text-amber-800 font-medium">⚠️ {warning.message}</span>
    </div>
  );
}

export function MarketingDashboard() {
  const { data: byChannel = [] } = useAnalyticsByChannel();
  const { data: byTopic = [] } = useAnalyticsByTopic();
  const { data: gaps = [] } = useAnalyticsGaps();
  const { data: density = [] } = useAnalyticsDensity();
  const { data: warnings = [] } = useAnalyticsWarnings();
  const notifyUpcoming = useNotifyUpcoming();
  const [notifyResult, setNotifyResult] = useState<number | null>(null);

  // Метрики из аналитики
  const totalPlanned = density.reduce((s, r) => s + (r.posts_planned || 0), 0);
  const approvedCount = byChannel
    .filter((r) => r.status_code === 'approved')
    .reduce((s, r) => s + r.posts, 0);
  const publishedCount = byChannel
    .filter((r) => r.status_code === 'published')
    .reduce((s, r) => s + r.posts, 0);
  const gapsCount = gaps.length;

  const handleNotify = async () => {
    const res = await notifyUpcoming.mutateAsync();
    setNotifyResult(res.notified_post_ids.length);
    setTimeout(() => setNotifyResult(null), 3000);
  };

  const channelColumns = [
    { key: 'channel', header: 'Канал', render: (r: DistributionRow) => r.channel || '—' },
    { key: 'status_code', header: 'Статус' },
    { key: 'posts', header: 'Постов', className: 'text-right' },
  ];

  const topicColumns = [
    { key: 'topic', header: 'Рубрика', render: (r: DistributionRow) => r.topic || '—' },
    { key: 'status_code', header: 'Статус' },
    { key: 'posts', header: 'Постов', className: 'text-right' },
  ];

  const gapColumns = [
    { key: 'day', header: 'День' },
    { key: 'channel', header: 'Канал' },
    {
      key: 'planned_posts',
      header: 'Запланировано',
      render: (r: GapRow) => (
        <span className="text-[#EF4444] font-medium">{r.planned_posts}</span>
      ),
    },
  ];

  // Составные ключи для таблиц без natural id
  const channelKey = (r: DistributionRow) => `${r.channel}-${r.status_code}`;
  const topicKey = (r: DistributionRow) => `${r.topic}-${r.status_code}`;
  const gapKey = (r: GapRow) => `${r.day}-${r.channel}`;

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-[#1E293B]">Маркетинг</h1>
          <p className="text-[#64748B] mt-1">Аналитика контент-плана</p>
        </div>
        <Button onClick={handleNotify} loading={notifyUpcoming.isPending} variant="secondary">
          <AlertCircle className="w-4 h-4" />
          Напомнить о дедлайнах
        </Button>
      </div>

      {notifyResult !== null && (
        <div className="mb-6 p-4 bg-[#ECFDF5] border border-[#10B981] rounded-lg text-[#10B981]">
          Отправлено уведомлений: {notifyResult}
        </div>
      )}

      {/* Индикаторы «провалов» (ТЗ п.4.3) */}
      {warnings.length > 0 && (
        <div className="mb-6 space-y-2">
          {warnings.map((w, i) => <WarningBanner key={i} warning={w} />)}
        </div>
      )}

      {/* Метрики */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <MetricCard
          title="Запланировано постов"
          value={totalPlanned}
          icon={CalendarDays}
          iconColor="text-[#2563EB]"
          iconBg="bg-blue-50"
        />
        <MetricCard
          title="Утверждено"
          value={approvedCount}
          icon={CheckCircle}
          iconColor="text-[#10B981]"
          iconBg="bg-[#ECFDF5]"
        />
        <MetricCard
          title="Опубликовано"
          value={publishedCount}
          icon={LayoutList}
          iconColor="text-[#8B5CF6]"
          iconBg="bg-purple-50"
        />
        <MetricCard
          title="Пропуски на неделе"
          value={gapsCount}
          icon={AlertCircle}
          iconColor={gapsCount > 0 ? 'text-[#EF4444]' : 'text-[#10B981]'}
          iconBg={gapsCount > 0 ? 'bg-[#FEF2F2]' : 'bg-[#ECFDF5]'}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Распределение по каналам */}
        <Card>
          <CardHeader title="По каналам" description="Распределение постов по каналам публикации" />
          <CardContent className="p-0">
            <Table
              columns={channelColumns}
              data={byChannel}
              keyExtractor={channelKey}
              emptyMessage="Нет данных"
            />
          </CardContent>
        </Card>

        {/* Распределение по рубрикам */}
        <Card>
          <CardHeader title="По рубрикам" description="Распределение постов по тематикам" />
          <CardContent className="p-0">
            <Table
              columns={topicColumns}
              data={byTopic}
              keyExtractor={topicKey}
              emptyMessage="Нет данных"
            />
          </CardContent>
        </Card>
      </div>

      {/* Пропуски */}
      {gapsCount > 0 && (
        <Card>
          <CardHeader
            title="Пропуски на ближайшей неделе"
            description="Каналы и дни без запланированного контента"
          />
          <CardContent className="p-0">
            <Table
              columns={gapColumns}
              data={gaps}
              keyExtractor={gapKey}
              emptyMessage="Контент-план заполнен"
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
