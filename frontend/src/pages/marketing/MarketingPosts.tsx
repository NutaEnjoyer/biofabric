import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Filter } from 'lucide-react';
import {
  Card, CardHeader, CardContent, Table, Select, Button, Badge, Modal, Input,
} from '../../components/ui';
import { usePosts, useCreatePost } from '../../hooks/useMarketing';
import type { Post, PostStatus, PostSourceCode } from '../../types/marketing';

const statusOptions = [
  { value: '', label: 'Все статусы' },
  { value: 'draft', label: 'Черновик' },
  { value: 'in_review', label: 'На проверке' },
  { value: 'approved', label: 'Утверждён' },
  { value: 'scheduled', label: 'Запланирован' },
  { value: 'published', label: 'Опубликован' },
  { value: 'archived', label: 'Архив' },
];

const statusConfig: Record<PostStatus, { label: string; variant: 'default' | 'warning' | 'success' | 'info' | 'danger' }> = {
  draft:     { label: 'Черновик',    variant: 'default' },
  in_review: { label: 'На проверке', variant: 'warning' },
  approved:  { label: 'Утверждён',   variant: 'success' },
  scheduled: { label: 'Запланирован',variant: 'info' },
  published: { label: 'Опубликован', variant: 'success' },
  archived:  { label: 'Архив',       variant: 'default' },
};

function PostStatusBadge({ status }: { status: string }) {
  const cfg = statusConfig[status as PostStatus] ?? { label: status, variant: 'default' };
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>;
}

const sourceLabels: Record<PostSourceCode, string> = {
  manual: 'Вручную',
  ai_generated: 'ИИ',
  external_source: 'Внешний',
  archive: 'Архив',
};

function SourceLabel({ source }: { source?: PostSourceCode }) {
  const label = sourceLabels[source ?? 'manual'] ?? 'Вручную';
  const isAI = source === 'ai_generated';
  return (
    <span className={`text-xs ${isAI ? 'text-purple-700 font-medium' : 'text-[#64748B]'}`}>
      {label}
    </span>
  );
}

export function MarketingPosts() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ title: '', text: '', channel_id: '1', format_id: '1', topic_id: '1' });

  const { data: posts = [], isLoading } = usePosts();
  const createPost = useCreatePost();

  const filtered = statusFilter
    ? posts.filter((p) => p.status_code === statusFilter)
    : posts;

  const handleCreate = async () => {
    await createPost.mutateAsync({
      title: form.title,
      text: form.text,
      channel_id: Number(form.channel_id),
      format_id: Number(form.format_id),
      topic_id: Number(form.topic_id),
    });
    setShowCreate(false);
    setForm({ title: '', text: '', channel_id: '1', format_id: '1', topic_id: '1' });
  };

  const columns = [
    {
      key: 'post_id',
      header: '№',
      render: (p: Post) => <span className="font-medium text-[#2563EB]">#{p.post_id}</span>,
    },
    {
      key: 'title',
      header: 'Заголовок',
      render: (p: Post) => p.title || <span className="text-[#94A3B8] italic">Без заголовка</span>,
    },
    {
      key: 'source_code',
      header: 'Источник',
      render: (p: Post) => <SourceLabel source={p.source_code} />,
    },
    {
      key: 'status_code',
      header: 'Статус',
      render: (p: Post) => <PostStatusBadge status={p.status_code} />,
    },
    {
      key: 'planned_for',
      header: 'Дата',
      render: (p: Post) => p.planned_for || <span className="text-[#94A3B8]">—</span>,
    },
    {
      key: 'hashtags',
      header: 'Хэштеги',
      render: (p: Post) =>
        p.hashtags?.length
          ? <span className="text-[#64748B] text-xs">{p.hashtags.slice(0, 3).join(' ')}</span>
          : <span className="text-[#94A3B8]">—</span>,
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-[#1E293B]">Посты</h1>
          <p className="text-[#64748B] mt-1">Все публикации и черновики</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="w-4 h-4" />
          Создать пост
        </Button>
      </div>

      <Card>
        <CardHeader
          title="Список постов"
          description={`Найдено: ${filtered.length}`}
          action={
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-[#64748B]" />
              <Select
                options={statusOptions}
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-48"
              />
            </div>
          }
        />
        <CardContent className="p-0">
          <Table
            columns={columns}
            data={filtered}
            keyExtractor={(p) => p.post_id}
            onRowClick={(p) => navigate(`/marketing/posts/${p.post_id}`)}
            loading={isLoading}
            emptyMessage="Посты не найдены"
          />
        </CardContent>
      </Card>

      {/* Модалка создания поста */}
      <Modal
        isOpen={showCreate}
        onClose={() => setShowCreate(false)}
        title="Новый пост"
      >
        <div className="space-y-4">
          <Input
            label="Заголовок"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="Заголовок поста"
          />
          <div>
            <label className="block text-sm font-medium text-[#374151] mb-1">Текст</label>
            <textarea
              className="w-full border border-[#E2E8F0] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB] min-h-[120px]"
              value={form.text}
              onChange={(e) => setForm({ ...form, text: e.target.value })}
              placeholder="Текст публикации..."
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={() => setShowCreate(false)}>Отмена</Button>
            <Button onClick={handleCreate} loading={createPost.isPending}>Создать</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
