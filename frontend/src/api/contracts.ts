import { api } from './client';
import type {
  Contract,
  ContractListResponse,
  ContractShort,
  BindWorkflowResponse,
  GuaranteeShare,
  ContractIssueRow,
  ValidatePartiesResponse,
  SendTemplateRequest,
  SendTemplateResponse,
  EISEnqueueRequest,
  EISEnqueueResponse,
  Import1CStageRequest,
  Import1CStageResponse,
  Import1CUpsertResponse,
  TimelineEntry,
  ContractAIAnalysis,
  StartAnalysisResponse,
  Send1CResponse,
} from '../types/contracts';

// Contracts CRUD
export const getContracts = async (params?: { status_code?: string; limit?: number; offset?: number }) => {
  const { data } = await api.get<ContractListResponse>('/contracts', { params });
  return data;
};

export const getContract = async (id: number) => {
  const { data } = await api.get<Contract>(`/contracts/${id}`);
  return data;
};

// Workflow
export const bindWorkflow = async (contractId: number) => {
  const { data } = await api.post<BindWorkflowResponse>(`/contracts/${contractId}/workflow/bind`);
  return data;
};

// Deadlines
export const syncDeadlines = async (contractId: number) => {
  const { data } = await api.post<{ created: number }>(`/contracts/${contractId}/sync-deadlines`);
  return data;
};

// Mark overdue
export const markOverdue = async () => {
  const { data } = await api.post<{ affected: number }>('/contracts/mark-overdue');
  return data;
};

// Without guarantee
export const getContractsWithoutGuarantee = async () => {
  const { data } = await api.get<ContractShort[]>('/contracts/without-guarantee');
  return data;
};

// Validate parties
export const validateParties = async (contractId: number) => {
  const { data } = await api.get<ValidatePartiesResponse>(`/contracts/${contractId}/validate-parties`);
  return data;
};

// KPI
export const getGuaranteeShare = async () => {
  const { data } = await api.get<GuaranteeShare>('/kpi/guarantee-share');
  return data;
};

export const getIssues = async (minSeverity?: number) => {
  const { data } = await api.get<ContractIssueRow[]>('/kpi/issues', {
    params: minSeverity ? { min_severity: minSeverity } : undefined,
  });
  return data;
};

// Notifications
export const sendNotification = async (request: SendTemplateRequest) => {
  const { data } = await api.post<SendTemplateResponse>('/notifications/send', request);
  return data;
};

// EIS
export const enqueueEIS = async (request: EISEnqueueRequest) => {
  const { data } = await api.post<EISEnqueueResponse>('/eis/enqueue', request);
  return data;
};

// 1C Import
export const stage1C = async (request: Import1CStageRequest) => {
  const { data } = await api.post<Import1CStageResponse>('/import/1c/stage', request);
  return data;
};

export const upsert1C = async (stageId: number) => {
  const { data } = await api.post<Import1CUpsertResponse>(`/import/1c/upsert/${stageId}`);
  return data;
};

// ─── Таймлайн ────────────────────────────────────────────────────────────────

export const getTimeline = async (contractId: number) => {
  const { data } = await api.get<TimelineEntry[]>(`/contracts/${contractId}/timeline`);
  return data;
};

// ─── ИИ-анализ ───────────────────────────────────────────────────────────────

export const getAIAnalysis = async (contractId: number) => {
  const { data } = await api.get<ContractAIAnalysis | { status: 'not_started' }>(
    `/contracts/${contractId}/ai-analysis`
  );
  return data;
};

export const startAIAnalysis = async (contractId: number) => {
  const { data } = await api.post<StartAnalysisResponse>(
    `/contracts/${contractId}/ai-analysis/start`
  );
  return data;
};

// ─── Отправка в 1С ───────────────────────────────────────────────────────────

export const sendTo1C = async (contractId: number) => {
  const { data } = await api.post<Send1CResponse>(`/contracts/${contractId}/send-to-1c`);
  return data;
};
