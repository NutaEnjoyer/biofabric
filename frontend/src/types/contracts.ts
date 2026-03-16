export interface Contract {
  contract_id: number;
  contract_no: string;
  title: string;
  type_code?: string;
  status_code: string;
  sign_date?: string;
  start_date?: string;
  end_date?: string;
  performance_due?: string;
  payment_due?: string;
  amount_total?: number;
  currency?: string;
  initiator_user_id?: number;
  responsible_user_id?: number;
  created_at: string;
  updated_at?: string;
  // Источник и интеграция
  source_code?: string;              // 'manual' | '1c_import'
  integration_1c_status?: string;   // 'not_sent' | 'queued' | 'sent' | 'error'
  integration_1c_error?: string;
  integration_1c_sent_at?: string;
  // Риски и отклонения
  risks_cnt?: number;
  has_critical_risk?: boolean;
  deviations_cnt?: number;
  // Гарантия
  has_active_guarantee?: boolean;
  // ЕИС
  eis_status?: string;
  eis_updated_at?: string;
}

export interface ContractShort {
  contract_id: number;
  contract_no: string;
  title?: string;
  status_code?: string;
  end_date?: string;
  amount_total?: number;
  // Индикаторы реестра
  source_code?: string;
  is_overdue_flag?: boolean;
  has_active_guarantee?: boolean;
  has_deviations?: boolean;
}

export interface ContractListResponse {
  items: ContractShort[];
  count: number;
}

export interface BindWorkflowResponse {
  wf_instance_id: number;
  status: 'bound' | 'already_bound';
}

export interface GuaranteeShare {
  with_guarantee: number;
  total: number;
  pct: number;
}

export interface ContractIssueRow {
  contract_id: number;
  risks_cnt: number;
  deviations_cnt: number;
}

export interface ValidatePartiesResponse {
  issues: string[];
}

export interface SendTemplateRequest {
  template_code: string;
  to: string[];
  payload: Record<string, unknown>;
}

export interface SendTemplateResponse {
  outbox_id: number;
}

export interface EISEnqueueRequest {
  contract_id: number;
  payload: Record<string, unknown>;
}

export interface EISEnqueueResponse {
  queue_id: number;
  job_id: string;
}

export interface Import1CStageRequest {
  payload: Record<string, unknown>;
}

export interface Import1CStageResponse {
  stage_id: number;
}

export interface Import1CUpsertResponse {
  contract_id: number;
}

// ─── Таймлайн ────────────────────────────────────────────────────────────────

export interface TimelineEntry {
  history_id: number;
  field_name: string;
  old_value?: string;
  new_value?: string;
  changed_by?: number;
  changed_at: string;
  reason?: string;
}

// ─── ИИ-анализ ───────────────────────────────────────────────────────────────

export interface ContractAIAnalysis {
  analysis_id: number;
  status: 'pending' | 'running' | 'done' | 'needs_rerun' | 'not_started';
  analyzed_by?: number;
  analyzed_at?: string;
  document_version?: string;
  deviations_count: number;
  has_critical_risk: boolean;
  summary_text?: string;
  details_json?: Record<string, unknown>;
  created_at: string;
  updated_at?: string;
}

export interface StartAnalysisResponse {
  analysis_id: number;
  status: string;
}

// ─── Отправка в 1С ───────────────────────────────────────────────────────────

export interface Send1CResponse {
  status: string;
  job_id?: string;
  message?: string;
}
