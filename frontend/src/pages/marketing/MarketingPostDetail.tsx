import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Send, Sparkles, RefreshCw } from 'lucide-react';
import { Card, CardHeader, CardContent, Button, Input, Badge } from '../../components/ui';
import {
  usePost, useUpdatePost, useSetPostStatus, useSetPostDate, usePublishPost,
  useAIGeneratePostText, useAIRewritePost,
} from '../../hooks/useMarketing';
import type { PostStatus, PostSourceCode, AIPostTextResponse } from '../../types/marketing';

const statusConfig: Record<PostStatus, { label: string; variant: 'default' | 'warning' | 'success' | 'info' | 'danger' }> = {
  draft:     { label: 'Черновик',     variant: 'default' },
  in_review: { label: 'На проверке',  variant: 'warning' },
  approved:  { label: 'Утверждён',    variant: 'success' },
  scheduled: { label: 'Запланирован', variant: 'info' },
  published: { label: 'Опубликован',  variant: 'success' },
  archived:  { label: 'Архив',        variant: 'default' },
};

const sourceConfig: Record<PostSourceCode, { label: string; color: string }> = {
  manual:          { label: 'Вручную',         color: 'bg-gray-100 text-gray-600' },
  ai_generated:    { label: 'ИИ',              color: 'bg-purple-100 text-purple-700' },
  external_source: { label: 'Внешний источник', color: 'bg-blue-100 text-blue-700' },
  archive:         { label: 'Архив',           color: 'bg-yellow-100 text-yellow-700' },
};

// Допустимые переходы из текущего статуса
const transitions: Record<PostStatus, { to: PostStatus; label: string }[]> = {
  draft:     [{ to: 'in_review', label: 'На проверку' }],
  in_review: [{ to: 'approved', label: 'Утвердить' }, { to: 'draft', label: 'Вернуть в черновик' }],
  approved:  [{ to: 'archived', label: 'В архив' }],
  scheduled: [],
  published: [{ to: 'archived', label: 'В архив' }],
  archived:  [],
};

// Бейдж источника (ТЗ п.4.4)
function SourceBadge({ source }: { source?: PostSourceCode }) {
  const cfg = sourceConfig[source ?? 'manual'] ?? sourceConfig.manual;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cfg.color}`}>
      {cfg.label}
    </span>
  );
}

// Блок предложения ИИ (ТЗ п.2.1 — обязательный дисклеймер)
function AISuggestion({
  suggestion,
  onApply,
  onDismiss,
}: {
  suggestion: AIPostTextResponse;
  onApply: () => void;
  onDismiss: () => void;
}) {
  return (
    <div className="border border-purple-200 bg-purple-50 rounded-lg p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Sparkles className="w-4 h-4 text-purple-600" />
        <span className="text-sm font-medium text-purple-700">Предложение ИИ</span>
      </div>

      {/* Дисклеймер — обязателен по ТЗ п.7 */}
      <div className="text-xs text-purple-600 bg-purple-100 rounded px-3 py-2">
        ⚠️ {suggestion.disclaimer}
      </div>

      {suggestion.title && (
        <div>
          <span className="text-xs text-[#64748B] uppercase tracking-wide">Заголовок</span>
          <p className="text-sm font-semibold text-[#1E293B] mt-0.5">{suggestion.title}</p>
        </div>
      )}
      <div>
        <span className="text-xs text-[#64748B] uppercase tracking-wide">Текст</span>
        <p className="text-sm text-[#374151] whitespace-pre-wrap mt-0.5 leading-relaxed">{suggestion.body_md}</p>
      </div>
      {suggestion.hashtags?.length ? (
        <div className="flex flex-wrap gap-1">
          {suggestion.hashtags.map((tag) => (
            <span key={tag} className="text-xs text-purple-700 bg-purple-100 px-2 py-0.5 rounded-full">{tag}</span>
          ))}
        </div>
      ) : null}

      <div className="flex gap-2 pt-1">
        <Button className="flex-1" onClick={onApply}>Применить</Button>
        <Button variant="secondary" className="flex-1" onClick={onDismiss}>Отклонить</Button>
      </div>
    </div>
  );
}

export function MarketingPostDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const postId = Number(id);

  const { data: post, isLoading } = usePost(postId);
  const updatePost = useUpdatePost();
  const setStatus = useSetPostStatus();
  const setDate = useSetPostDate();
  const publishPost = usePublishPost();
  const generateText = useAIGeneratePostText();
  const rewriteText = useAIRewritePost();

  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ title: '', text: '', audience: '', goals: '', tone: '', hashtags: '' });
  const [newDate, setNewDate] = useState('');
  const [publishError, setPublishError] = useState<string | null>(null);
  const [publishUrl, setPublishUrl] = useState<string | null>(null);
  const [actionResult, setActionResult] = useState<string | null>(null);
  const [aiSuggestion, setAiSuggestion] = useState<AIPostTextResponse | null>(null);

  const startEdit = () => {
    if (!post) return;
    setForm({
      title: post.title || '',
      text: post.body_md || '',
      audience: post.audience || '',
      goals: post.goals || '',
      tone: post.tone || '',
      hashtags: (post.hashtags || []).join(', '),
    });
    setEditing(true);
  };

  const handleSave = async () => {
    await updatePost.mutateAsync({
      id: postId,
      payload: {
        title: form.title || undefined,
        text: form.text || undefined,
        audience: form.audience || undefined,
        goals: form.goals || undefined,
        tone: form.tone || undefined,
        hashtags: form.hashtags ? form.hashtags.split(',').map((t) => t.trim()).filter(Boolean) : undefined,
      },
    });
    setEditing(false);
    notify('Сохранено');
  };

  const handleStatus = async (status: PostStatus) => {
    await setStatus.mutateAsync({ id: postId, status });
    notify(`Статус изменён: ${statusConfig[status]?.label}`);
  };

  const handleSetDate = async () => {
    if (!newDate) return;
    await setDate.mutateAsync({ id: postId, ymd: newDate });
    setNewDate('');
    notify(`Дата назначена: ${newDate}`);
  };

  const handlePublish = async (platform: 'tg' | 'vk') => {
    setPublishError(null);
    setPublishUrl(null);
    const res = await publishPost.mutateAsync({ id: postId, platform });
    if (res.ok) {
      setPublishUrl(res.external_url ?? null);
    } else {
      // Показываем ошибку с текстом (ТЗ п.5)
      setPublishError(res.error_message ?? 'Ошибка публикации');
    }
  };

  const handleAIGenerate = async () => {
    setAiSuggestion(null);
    const res = await generateText.mutateAsync({ postId, payload: {} });
    setAiSuggestion(res);
  };

  const handleAIRewrite = async () => {
    setAiSuggestion(null);
    const res = await rewriteText.mutateAsync({ postId, payload: {} });
    setAiSuggestion(res);
  };

  const applyAISuggestion = async () => {
    if (!aiSuggestion) return;
    await updatePost.mutateAsync({
      id: postId,
      payload: {
        title: aiSuggestion.title || undefined,
        text: aiSuggestion.body_md,
        hashtags: aiSuggestion.hashtags,
      },
    });
    setAiSuggestion(null);
    notify('Текст ИИ применён');
  };

  const notify = (msg: string) => {
    setActionResult(msg);
    setTimeout(() => setActionResult(null), 3000);
  };

  if (isLoading) {
    return <div className="flex items-center justify-center py-20 text-[#64748B]">Загрузка...</div>;
  }

  if (!post) {
    return <div className="py-20 text-center text-[#64748B]">Пост не найден</div>;
  }

  const cfg = statusConfig[post.status_code] ?? { label: post.status_code, variant: 'default' };
  const availableTransitions = transitions[post.status_code] ?? [];

  return (
    <div>
      {/* Шапка */}
      <div className="flex items-center gap-4 mb-8">
        <button
          onClick={() => navigate(-1)}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-[#64748B]" />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-bold text-[#1E293B]">Пост #{post.post_id}</h1>
            {/* Статус — всегда виден цветом + текстом (ТЗ п.3) */}
            <Badge variant={cfg.variant}>{cfg.label}</Badge>
            {/* Источник (ТЗ п.4.4) */}
            <SourceBadge source={post.source_code} />
          </div>
          {post.planned_for && (
            <p className="text-[#64748B] mt-1">Дата публикации: {post.planned_for}</p>
          )}
        </div>
        {!editing ? (
          <Button variant="secondary" onClick={startEdit}>Редактировать</Button>
        ) : (
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => setEditing(false)}>Отмена</Button>
            <Button onClick={handleSave} loading={updatePost.isPending}>Сохранить</Button>
          </div>
        )}
      </div>

      {actionResult && (
        <div className="mb-4 p-3 bg-[#ECFDF5] border border-[#10B981] rounded-lg text-[#10B981] text-sm">
          {actionResult}
        </div>
      )}

      {/* Успешная публикация */}
      {publishUrl && (
        <div className="mb-4 p-3 bg-blue-50 border border-[#2563EB] rounded-lg text-[#2563EB] text-sm break-all">
          Опубликовано: <a href={publishUrl} target="_blank" rel="noreferrer" className="underline">{publishUrl}</a>
        </div>
      )}

      {/* Ошибка публикации — с текстом, не меняет контент (ТЗ п.5) */}
      {publishError && (
        <div className="mb-4 p-3 bg-red-50 border border-[#EF4444] rounded-lg text-[#EF4444] text-sm">
          Ошибка публикации: {publishError}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Основной контент */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader title="Контент" />
            <CardContent className="space-y-4">
              {editing ? (
                <>
                  <Input
                    label="Заголовок"
                    value={form.title}
                    onChange={(e) => setForm({ ...form, title: e.target.value })}
                  />
                  <div>
                    <label className="block text-sm font-medium text-[#374151] mb-1">Текст</label>
                    <textarea
                      className="w-full border border-[#E2E8F0] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB] min-h-[180px]"
                      value={form.text}
                      onChange={(e) => setForm({ ...form, text: e.target.value })}
                    />
                  </div>
                  <Input
                    label="Хэштеги (через запятую)"
                    value={form.hashtags}
                    onChange={(e) => setForm({ ...form, hashtags: e.target.value })}
                    placeholder="#биофабрика, #наука"
                  />
                </>
              ) : (
                <>
                  {post.title && <h2 className="text-lg font-semibold text-[#1E293B]">{post.title}</h2>}
                  {post.body_md ? (
                    <p className="text-[#374151] whitespace-pre-wrap text-sm leading-relaxed">{post.body_md}</p>
                  ) : (
                    <p className="text-[#94A3B8] italic text-sm">Текст не заполнен</p>
                  )}
                  {post.hashtags?.length ? (
                    <div className="flex flex-wrap gap-2 pt-2">
                      {post.hashtags.map((tag) => (
                        <span key={tag} className="text-xs text-[#2563EB] bg-blue-50 px-2 py-0.5 rounded-full">{tag}</span>
                      ))}
                    </div>
                  ) : null}
                </>
              )}

              {/* Кнопки ИИ (ТЗ п.2.2 — точка 2) */}
              {post.status_code !== 'published' && post.status_code !== 'archived' && (
                <div className="flex gap-2 pt-2 border-t border-[#E2E8F0]">
                  <Button
                    variant="secondary"
                    className="flex-1 text-purple-700 border-purple-200 hover:bg-purple-50"
                    onClick={handleAIGenerate}
                    loading={generateText.isPending}
                  >
                    <Sparkles className="w-4 h-4" />
                    Сгенерировать текст (ИИ)
                  </Button>
                  <Button
                    variant="secondary"
                    className="flex-1"
                    onClick={handleAIRewrite}
                    loading={rewriteText.isPending}
                  >
                    <RefreshCw className="w-4 h-4" />
                    Переписать под стиль Биофабрики
                  </Button>
                </div>
              )}

              {/* Предложение ИИ — со статусом без применения (ТЗ п.2.1) */}
              {aiSuggestion && (
                <AISuggestion
                  suggestion={aiSuggestion}
                  onApply={applyAISuggestion}
                  onDismiss={() => setAiSuggestion(null)}
                />
              )}
            </CardContent>
          </Card>

          {/* Параметры тона/ЦА */}
          <Card>
            <CardHeader title="Параметры контента" />
            <CardContent className="space-y-4">
              {editing ? (
                <>
                  <Input label="Целевая аудитория" value={form.audience} onChange={(e) => setForm({ ...form, audience: e.target.value })} />
                  <Input label="Цели публикации" value={form.goals} onChange={(e) => setForm({ ...form, goals: e.target.value })} />
                  <Input label="Tone of voice" value={form.tone} onChange={(e) => setForm({ ...form, tone: e.target.value })} />
                </>
              ) : (
                <div className="grid grid-cols-1 gap-3">
                  {[
                    { label: 'Источник', value: sourceConfig[post.source_code ?? 'manual']?.label },
                    { label: 'Целевая аудитория', value: post.audience },
                    { label: 'Цели', value: post.goals },
                    { label: 'Tone of voice', value: post.tone },
                  ].map(({ label, value }) => (
                    <div key={label}>
                      <dt className="text-xs text-[#64748B] uppercase tracking-wide">{label}</dt>
                      <dd className="text-sm text-[#1E293B] mt-0.5">{value || <span className="text-[#94A3B8]">—</span>}</dd>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Боковая панель действий */}
        <div className="space-y-4">
          {/* Статусы */}
          {availableTransitions.length > 0 && (
            <Card>
              <CardHeader title="Смена статуса" />
              <CardContent className="space-y-2">
                {availableTransitions.map(({ to, label }) => (
                  <Button
                    key={to}
                    variant="secondary"
                    className="w-full justify-start"
                    onClick={() => handleStatus(to)}
                    loading={setStatus.isPending}
                  >
                    {label}
                  </Button>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Назначить дату */}
          {post.status_code !== 'published' && post.status_code !== 'archived' && (
            <Card>
              <CardHeader title="Дата публикации" />
              <CardContent className="space-y-3">
                <Input
                  type="date"
                  value={newDate}
                  onChange={(e) => setNewDate(e.target.value)}
                />
                <Button
                  className="w-full"
                  onClick={handleSetDate}
                  loading={setDate.isPending}
                  disabled={!newDate}
                >
                  Назначить дату
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Публикация — только вручную, по кнопке (ТЗ п.5) */}
          {(post.status_code === 'approved' || post.status_code === 'scheduled') && (
            <Card>
              <CardHeader title="Опубликовать сейчас" />
              <CardContent className="space-y-2">
                <Button
                  className="w-full justify-start"
                  onClick={() => handlePublish('tg')}
                  loading={publishPost.isPending}
                >
                  <Send className="w-4 h-4" />
                  Telegram
                </Button>
                <Button
                  variant="secondary"
                  className="w-full justify-start"
                  onClick={() => handlePublish('vk')}
                  loading={publishPost.isPending}
                >
                  <Send className="w-4 h-4" />
                  ВКонтакте
                </Button>
                <p className="text-xs text-[#94A3B8] pt-1">
                  Публикация выполняется вручную. Автопостинг не предусмотрен.
                </p>
              </CardContent>
            </Card>
          )}

          {/* Ссылка после публикации */}
          {post.external_url && (
            <Card>
              <CardContent className="py-3">
                <p className="text-xs text-[#64748B] mb-1">Ссылка на публикацию</p>
                <a
                  href={post.external_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-[#2563EB] hover:underline break-all"
                >
                  {post.external_url}
                </a>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
