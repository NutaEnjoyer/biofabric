// ─── Post ─────────────────────────────────────────────────────────────────────

export type PostStatus =
  | 'draft'
  | 'in_review'
  | 'approved'
  | 'scheduled'
  | 'published'
  | 'archived';

export type Platform = 'tg' | 'vk';
export type SourceKind = 'tg' | 'url' | 'rss';
export type PostSourceCode = 'manual' | 'ai_generated' | 'external_source' | 'archive';

export interface Post {
  post_id: number;
  status_code: PostStatus;
  source_code: PostSourceCode;
  channel_id?: number;
  format_id?: number;
  topic_id?: number;
  direction_id?: number;
  title?: string;
  body_md?: string;
  hashtags?: string[];
  planned_for?: string;
  audience?: string;
  goals?: string;
  tone?: string;
  external_url?: string;
}

export interface PostCreate {
  channel_id: number;
  format_id: number;
  topic_id: number;
  direction_id?: number;
  title?: string;
  text?: string;
  planned_for?: string;
  source_code?: PostSourceCode;
  audience?: string;
  goals?: string;
  tone?: string;
  hashtags?: string[];
}

export interface PostUpdate {
  title?: string;
  text?: string;
  planned_for?: string;
  channel_id?: number;
  format_id?: number;
  topic_id?: number;
  direction_id?: number;
  audience?: string;
  goals?: string;
  tone?: string;
  hashtags?: string[];
}

// ─── Source ───────────────────────────────────────────────────────────────────

export interface Source {
  source_id: number;
  name: string;
  url: string;
  kind?: SourceKind;
  approved: boolean;
}

export interface SourceCreate {
  name: string;
  url: string;
  kind?: SourceKind;
}

// ─── Plan Job ─────────────────────────────────────────────────────────────────

export type PlanJobStatus = 'pending' | 'running' | 'done' | 'failed';

export interface PlanJob {
  job_id: number;
  period_start: string;
  period_end: string;
  direction_id?: number;
  audience?: string;
  goals?: string;
  tone?: string;
  status: PlanJobStatus;
  created_by?: number;
}

export interface PlanJobCreate {
  period_start: string;
  period_end: string;
  direction_id?: number;
  audience?: string;
  goals?: string;
  tone?: string;
}

// ─── Analytics ────────────────────────────────────────────────────────────────

export interface PlanSummaryRow {
  day: string;
  channel: string;
  status_code: string;
  posts: number;
}

export interface DistributionRow {
  topic?: string;
  format?: string;
  channel?: string;
  status_code: string;
  posts: number;
}

export interface DensityRow {
  day: string;
  posts_planned: number;
}

export interface GapRow {
  day: string;
  channel: string;
  planned_posts: number;
}

// ─── Publish response ─────────────────────────────────────────────────────────

export interface PublishResponse {
  ok: boolean;
  external_url?: string;
  error_message?: string;
}

// ─── AI post operations (ТЗ п.2.2) ───────────────────────────────────────────

export interface AIPostTextRequest {
  style_hint?: string;
  extra_context?: string;
}

export interface AIPostTextResponse {
  title?: string;
  body_md: string;
  hashtags?: string[];
  disclaimer: string;
}

// ─── Content warnings (ТЗ п.4.3) ─────────────────────────────────────────────

export interface ContentWarning {
  type: 'content_gap' | 'topic_skew' | 'no_approved';
  level: 'warning' | 'error';
  message: string;
  details?: unknown;
}

// ─── Generic response wrapper ─────────────────────────────────────────────────

export interface MkResponse<T = unknown> {
  ok: boolean;
  data?: T;
}
