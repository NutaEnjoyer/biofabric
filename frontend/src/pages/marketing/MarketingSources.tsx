import { useState } from 'react';
import { Plus, Trash2, ExternalLink } from 'lucide-react';
import { Card, CardHeader, CardContent, Table, Button, Input, Select, Badge } from '../../components/ui';
import { useSources, useCreateSource, useDeleteSource } from '../../hooks/useMarketing';
import type { Source, SourceKind } from '../../types/marketing';

const kindOptions = [
  { value: '', label: 'Не указан' },
  { value: 'url', label: 'Сайт / URL' },
  { value: 'rss', label: 'RSS-лента' },
  { value: 'tg', label: 'Telegram-канал' },
];

const kindLabels: Record<SourceKind, { label: string; variant: 'default' | 'info' | 'warning' | 'success' }> = {
  url: { label: 'URL',      variant: 'default' },
  rss: { label: 'RSS',      variant: 'info' },
  tg:  { label: 'Telegram', variant: 'success' },
};

export function MarketingSources() {
  const { data: sources = [], isLoading } = useSources();
  const createSource = useCreateSource();
  const deleteSource = useDeleteSource();

  const [form, setForm] = useState({ name: '', url: '', kind: '' as SourceKind | '' });
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const handleCreate = async () => {
    setError('');
    if (!form.name || !form.url) {
      setError('Заполните название и URL');
      return;
    }
    await createSource.mutateAsync({
      name: form.name,
      url: form.url,
      kind: form.kind || undefined,
    });
    setForm({ name: '', url: '', kind: '' });
    setSuccessMsg('Источник добавлен');
    setTimeout(() => setSuccessMsg(''), 3000);
  };

  const handleDelete = async (id: number, name: string) => {
    if (!confirm(`Удалить источник «${name}»?`)) return;
    await deleteSource.mutateAsync(id);
  };

  const columns = [
    {
      key: 'name',
      header: 'Название',
      render: (s: Source) => <span className="font-medium">{s.name}</span>,
    },
    {
      key: 'url',
      header: 'URL',
      render: (s: Source) => (
        <a
          href={s.url}
          target="_blank"
          rel="noreferrer"
          className="text-[#2563EB] hover:underline flex items-center gap-1 max-w-xs truncate"
          onClick={(e) => e.stopPropagation()}
        >
          {s.url}
          <ExternalLink className="w-3 h-3 flex-shrink-0" />
        </a>
      ),
    },
    {
      key: 'kind',
      header: 'Тип',
      render: (s: Source) => {
        if (!s.kind) return <span className="text-[#94A3B8]">—</span>;
        const cfg = kindLabels[s.kind];
        return <Badge variant={cfg?.variant ?? 'default'}>{cfg?.label ?? s.kind}</Badge>;
      },
    },
    {
      key: 'actions',
      header: '',
      render: (s: Source) => (
        <Button
          variant="danger"
          onClick={(e) => { e.stopPropagation(); handleDelete(s.source_id, s.name); }}
          loading={deleteSource.isPending}
          className="text-xs"
        >
          <Trash2 className="w-3 h-3" />
        </Button>
      ),
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-[#1E293B]">Источники контента</h1>
          <p className="text-[#64748B] mt-1">Whitelist внешних источников для сбора материалов</p>
        </div>
      </div>

      {/* Форма добавления */}
      <Card className="mb-6">
        <CardHeader title="Добавить источник" />
        <CardContent>
          {error && (
            <div className="mb-4 p-3 bg-[#FEF2F2] border border-[#EF4444] rounded-lg text-[#EF4444] text-sm">
              {error}
            </div>
          )}
          {successMsg && (
            <div className="mb-4 p-3 bg-[#ECFDF5] border border-[#10B981] rounded-lg text-[#10B981] text-sm">
              {successMsg}
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
            <Input
              label="Название"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Биотехнологии Today"
            />
            <div className="md:col-span-2">
              <Input
                label="URL"
                value={form.url}
                onChange={(e) => setForm({ ...form, url: e.target.value })}
                placeholder="https://example.com/feed"
              />
            </div>
            <Select
              label="Тип"
              options={kindOptions}
              value={form.kind}
              onChange={(e) => setForm({ ...form, kind: e.target.value as SourceKind | '' })}
            />
          </div>
          <div className="mt-4 flex justify-end">
            <Button onClick={handleCreate} loading={createSource.isPending}>
              <Plus className="w-4 h-4" />
              Добавить
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Список источников */}
      <Card>
        <CardHeader
          title="Список источников"
          description={`${sources.length} источников в whitelist`}
        />
        <CardContent className="p-0">
          <Table
            columns={columns}
            data={sources}
            keyExtractor={(s) => s.source_id}
            loading={isLoading}
            emptyMessage="Источники не добавлены"
          />
        </CardContent>
      </Card>
    </div>
  );
}
