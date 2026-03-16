import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CalendarDays, Lightbulb } from 'lucide-react';
import { Card, CardHeader, CardContent, Table, Input, Badge, Button } from '../../components/ui';
import { useCalendar, useIdeas, useReplacePost } from '../../hooks/useMarketing';
import type { Post, PostStatus } from '../../types/marketing';

const statusConfig: Record<PostStatus, { label: string; variant: 'default' | 'warning' | 'success' | 'info' | 'danger' }> = {
  draft:     { label: 'Черновик',     variant: 'default' },
  in_review: { label: 'На проверке',  variant: 'warning' },
  approved:  { label: 'Утверждён',    variant: 'success' },
  scheduled: { label: 'Запланирован', variant: 'info' },
  published: { label: 'Опубликован',  variant: 'success' },
  archived:  { label: 'Архив',        variant: 'default' },
};

function PostStatusBadge({ status }: { status: string }) {
  const cfg = statusConfig[status as PostStatus] ?? { label: status, variant: 'default' };
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>;
}

export function MarketingCalendar() {
  const navigate = useNavigate();
  const today = new Date().toISOString().split('T')[0];
  const nextMonth = new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0];

  const [periodFrom, setPeriodFrom] = useState(today);
  const [periodTo, setPeriodTo] = useState(nextMonth);

  // Для замены: выбранный пост на дате и идея из корзины
  const [replacing, setReplacing] = useState<{ date: string; postId: number } | null>(null);
  const [selectedIdeaId, setSelectedIdeaId] = useState<number | null>(null);
  const [replaceResult, setReplaceResult] = useState<string | null>(null);

  const { data: calendarPosts = [], isLoading } = useCalendar({ period_from: periodFrom, period_to: periodTo });
  const { data: ideas = [] } = useIdeas();
  const replacePost = useReplacePost();

  const handleReplace = async () => {
    if (!replacing || !selectedIdeaId) return;
    await replacePost.mutateAsync({
      date: replacing.date,
      post_id_to_remove: replacing.postId,
      idea_post_id_to_use: selectedIdeaId,
    });
    setReplaceResult(`Пост заменён идеей #${selectedIdeaId}`);
    setReplacing(null);
    setSelectedIdeaId(null);
    setTimeout(() => setReplaceResult(null), 3000);
  };

  const calendarColumns = [
    {
      key: 'planned_for',
      header: 'Дата',
      render: (p: Post) => <span className="font-medium">{p.planned_for}</span>,
    },
    {
      key: 'title',
      header: 'Заголовок',
      render: (p: Post) => p.title || <span className="text-[#94A3B8] italic">Без заголовка</span>,
    },
    {
      key: 'status_code',
      header: 'Статус',
      render: (p: Post) => <PostStatusBadge status={p.status_code} />,
    },
    {
      key: 'actions',
      header: '',
      render: (p: Post) => (
        <Button
          variant="ghost"
          onClick={(e) => {
            e.stopPropagation();
            setReplacing({ date: p.planned_for!, postId: p.post_id });
          }}
          className="text-xs"
        >
          Заменить
        </Button>
      ),
    },
  ];

  const ideaColumns = [
    {
      key: 'post_id',
      header: '№',
      render: (p: Post) => <span className="text-[#2563EB] font-medium">#{p.post_id}</span>,
    },
    {
      key: 'title',
      header: 'Заголовок',
      render: (p: Post) => p.title || <span className="text-[#94A3B8] italic">Без заголовка</span>,
    },
    {
      key: 'select',
      header: '',
      render: (p: Post) =>
        replacing ? (
          <Button
            variant={selectedIdeaId === p.post_id ? 'primary' : 'secondary'}
            onClick={(e) => { e.stopPropagation(); setSelectedIdeaId(p.post_id); }}
            className="text-xs"
          >
            {selectedIdeaId === p.post_id ? '✓ Выбрана' : 'Выбрать'}
          </Button>
        ) : null,
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-[#1E293B]">Контент-календарь</h1>
          <p className="text-[#64748B] mt-1">Расписание публикаций по датам</p>
        </div>
      </div>

      {replaceResult && (
        <div className="mb-4 p-4 bg-[#ECFDF5] border border-[#10B981] rounded-lg text-[#10B981]">
          {replaceResult}
        </div>
      )}

      {replacing && (
        <div className="mb-4 p-4 bg-blue-50 border border-[#2563EB] rounded-lg flex items-center justify-between">
          <span className="text-sm text-[#2563EB]">
            Замена поста #{replacing.postId} на дату {replacing.date} — выберите идею ниже
          </span>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => { setReplacing(null); setSelectedIdeaId(null); }}>
              Отмена
            </Button>
            <Button
              onClick={handleReplace}
              loading={replacePost.isPending}
              disabled={!selectedIdeaId}
            >
              Заменить
            </Button>
          </div>
        </div>
      )}

      {/* Фильтр периода */}
      <Card className="mb-6">
        <CardContent className="py-4">
          <div className="flex items-center gap-4">
            <CalendarDays className="w-5 h-5 text-[#64748B]" />
            <Input
              label="С"
              type="date"
              value={periodFrom}
              onChange={(e) => setPeriodFrom(e.target.value)}
              className="w-44"
            />
            <Input
              label="По"
              type="date"
              value={periodTo}
              onChange={(e) => setPeriodTo(e.target.value)}
              className="w-44"
            />
          </div>
        </CardContent>
      </Card>

      {/* Календарь */}
      <Card className="mb-6">
        <CardHeader
          title="Запланированные публикации"
          description={`${calendarPosts.length} постов за период`}
        />
        <CardContent className="p-0">
          <Table
            columns={calendarColumns}
            data={calendarPosts}
            keyExtractor={(p) => p.post_id}
            onRowClick={(p) => navigate(`/marketing/posts/${p.post_id}`)}
            loading={isLoading}
            emptyMessage="Нет запланированных постов"
          />
        </CardContent>
      </Card>

      {/* Корзина идей */}
      <Card>
        <CardHeader
          title="Корзина идей"
          description={`${ideas.length} идей без даты`}
          action={<Lightbulb className="w-5 h-5 text-[#F59E0B]" />}
        />
        <CardContent className="p-0">
          <Table
            columns={ideaColumns}
            data={ideas}
            keyExtractor={(p) => p.post_id}
            onRowClick={(p) => navigate(`/marketing/posts/${p.post_id}`)}
            emptyMessage="Корзина идей пуста"
          />
        </CardContent>
      </Card>
    </div>
  );
}
