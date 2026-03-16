import axios from 'axios';
import type {
  Post, PostCreate, PostUpdate,
  Source, SourceCreate,
  PlanJob, PlanJobCreate,
  PlanSummaryRow, DistributionRow, DensityRow, GapRow,
  PublishResponse, AIPostTextRequest, AIPostTextResponse, ContentWarning,
  MkResponse,
} from '../types/marketing';

// Separate axios instance — nginx proxies /api/marketing/* to marketing-service
const mkApi = axios.create({
  baseURL: '/api/marketing',
  headers: { 'Content-Type': 'application/json' },
});

mkApi.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail || err.message || 'Ошибка сервера';
    console.error('Marketing API Error:', msg);
    return Promise.reject(err);
  }
);

// Helper — unwrap the { ok, data } envelope
const unwrap = <T>(r: MkResponse<T>): T => r.data as T;

// ─── Posts ────────────────────────────────────────────────────────────────────

export const getPosts = async (params?: { period_from?: string; period_to?: string }) => {
  const { data } = await mkApi.get<MkResponse<Post[]>>('/posts', { params });
  return unwrap(data) ?? [];
};

export const getPost = async (id: number) => {
  const { data } = await mkApi.get<MkResponse<Post>>(`/posts/${id}`);
  return unwrap(data)!;
};

export const createPost = async (payload: PostCreate) => {
  const { data } = await mkApi.post<MkResponse<{ post_id: number }>>('/posts', payload);
  return unwrap(data)!;
};

export const updatePost = async ({ id, payload }: { id: number; payload: PostUpdate }) => {
  const { data } = await mkApi.patch<MkResponse>(`/posts/${id}`, payload);
  return unwrap(data);
};

export const setPostStatus = async ({ id, status }: { id: number; status: string }) => {
  const { data } = await mkApi.post<MkResponse>(`/posts/${id}/status/${status}`);
  return unwrap(data);
};

export const setPostDate = async ({ id, ymd }: { id: number; ymd: string }) => {
  const { data } = await mkApi.post<MkResponse>(`/posts/${id}/date`, null, { params: { ymd } });
  return unwrap(data);
};

export const publishPost = async ({ id, platform }: { id: number; platform: string }) => {
  const { data } = await mkApi.post<PublishResponse>(
    `/posts/${id}/publish`,
    { platform }
  );
  return data;
};

export const replacePost = async (payload: {
  date: string;
  post_id_to_remove: number;
  idea_post_id_to_use: number;
}) => {
  const { data } = await mkApi.post<MkResponse<{ post_id: number }>>('/posts/replace', payload);
  return unwrap(data)!;
};

// ─── Calendar ─────────────────────────────────────────────────────────────────

export const getCalendar = async (params?: { period_from?: string; period_to?: string }) => {
  const { data } = await mkApi.get<MkResponse<Post[]>>('/calendar', { params });
  return unwrap(data) ?? [];
};

export const getIdeas = async () => {
  const { data } = await mkApi.get<MkResponse<Post[]>>('/ideas');
  return unwrap(data) ?? [];
};

// ─── Sources ──────────────────────────────────────────────────────────────────

export const getSources = async () => {
  const { data } = await mkApi.get<MkResponse<Source[]>>('/sources');
  return unwrap(data) ?? [];
};

export const createSource = async (payload: SourceCreate) => {
  const { data } = await mkApi.post<MkResponse<{ source_id: number }>>('/sources', payload);
  return unwrap(data)!;
};

export const deleteSource = async (id: number) => {
  const { data } = await mkApi.delete<MkResponse>(`/sources/${id}`);
  return unwrap(data);
};

// ─── AI ───────────────────────────────────────────────────────────────────────

export const aiGeneratePlan = async (payload: {
  prompt: string;
  channels?: number[];
  formats?: number[];
}) => {
  const { data } = await mkApi.post<{ created_post_ids: number[] }>('/ai/plan', payload);
  return data;
};

export const aiGenerateIdeas = async (payload: {
  source_ids?: number[];
  limit_per_source?: number;
}) => {
  const { data } = await mkApi.post<{ created_post_ids: number[] }>('/ai/ideas', payload);
  return data;
};

export const aiGeneratePostText = async ({
  postId,
  payload,
}: {
  postId: number;
  payload: AIPostTextRequest;
}) => {
  const { data } = await mkApi.post<AIPostTextResponse>(
    `/posts/${postId}/ai/generate-text`,
    payload
  );
  return data;
};

export const aiRewritePost = async ({
  postId,
  payload,
}: {
  postId: number;
  payload: AIPostTextRequest;
}) => {
  const { data } = await mkApi.post<AIPostTextResponse>(
    `/posts/${postId}/ai/rewrite`,
    payload
  );
  return data;
};

// ─── Plan Jobs ────────────────────────────────────────────────────────────────

export const getPlanJobs = async () => {
  const { data } = await mkApi.get<MkResponse<PlanJob[]>>('/plan-jobs');
  return unwrap(data) ?? [];
};

export const createPlanJob = async (payload: PlanJobCreate) => {
  const { data } = await mkApi.post<MkResponse<{ job_id: number; created_post_ids: number[] }>>(
    '/plan-jobs',
    payload
  );
  return unwrap(data)!;
};

// ─── Analytics ────────────────────────────────────────────────────────────────

export const getAnalyticsSummary = async () => {
  const { data } = await mkApi.get<MkResponse<PlanSummaryRow[]>>('/analytics/summary');
  return unwrap(data) ?? [];
};

export const getAnalyticsByChannel = async () => {
  const { data } = await mkApi.get<MkResponse<DistributionRow[]>>('/analytics/by-channel');
  return unwrap(data) ?? [];
};

export const getAnalyticsByTopic = async () => {
  const { data } = await mkApi.get<MkResponse<DistributionRow[]>>('/analytics/by-topic');
  return unwrap(data) ?? [];
};

export const getAnalyticsByFormat = async () => {
  const { data } = await mkApi.get<MkResponse<DistributionRow[]>>('/analytics/by-format');
  return unwrap(data) ?? [];
};

export const getAnalyticsDensity = async () => {
  const { data } = await mkApi.get<MkResponse<DensityRow[]>>('/analytics/density');
  return unwrap(data) ?? [];
};

export const getAnalyticsGaps = async () => {
  const { data } = await mkApi.get<MkResponse<GapRow[]>>('/analytics/gaps');
  return unwrap(data) ?? [];
};

export const notifyUpcoming = async () => {
  const { data } = await mkApi.post<MkResponse<{ notified_post_ids: number[] }>>(
    '/analytics/notify-upcoming'
  );
  return unwrap(data)!;
};

export const getAnalyticsWarnings = async () => {
  const { data } = await mkApi.get<MkResponse<ContentWarning[]>>('/analytics/warnings');
  return unwrap(data) ?? [];
};
