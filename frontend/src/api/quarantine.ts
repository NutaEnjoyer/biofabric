import axios from 'axios';
import type {
  OperationCreate, IdResponse, ApiResponse,
  MonthlySummaryRow, Species, Direction,
  AgeCat, MassBin, Group, Cohort,
  DashboardData, DynamicsRow, HistoryEntry, VivariumGroup,
} from '../types/quarantine';

const qaApi = axios.create({
  baseURL: '/api/quarantine',
  headers: { 'Content-Type': 'application/json' },
});

qaApi.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail || err.message || 'Ошибка сервера';
    console.error('Quarantine API Error:', msg);
    return Promise.reject(err);
  }
);

// ─── Справочники ────────────────────────────────────────────────────────────

export const getSpecies = async () => {
  const { data } = await qaApi.get<Species[]>('/species');
  return data;
};

export const getDirections = async () => {
  const { data } = await qaApi.get<Direction[]>('/directions');
  return data;
};

export const getAgeCategories = async (speciesCode: string) => {
  const { data } = await qaApi.get<AgeCat[]>(`/species/${speciesCode}/age-categories`);
  return data;
};

export const getMassBins = async (speciesCode: string) => {
  const { data } = await qaApi.get<MassBin[]>(`/species/${speciesCode}/mass-bins`);
  return data;
};

export const getGroups = async () => {
  const { data } = await qaApi.get<Group[]>('/groups');
  return data;
};

export const getCohorts = async () => {
  const { data } = await qaApi.get<Cohort[]>('/cohorts');
  return data;
};

// ─── Операции ───────────────────────────────────────────────────────────────

export const createOperation = async (payload: OperationCreate) => {
  const { data } = await qaApi.post<IdResponse>('/operations', payload);
  return data;
};

export const confirmOperation = async (entryId: number) => {
  const { data } = await qaApi.patch<ApiResponse>(`/operations/${entryId}/confirm`);
  return data;
};

// ─── Импорт ─────────────────────────────────────────────────────────────────

export const importCsv = async (file: File) => {
  const form = new FormData();
  form.append('file', file);
  const { data } = await qaApi.post<ApiResponse>('/import', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

// ─── Отчёты ─────────────────────────────────────────────────────────────────

export const getMonthlySummary = async (periodMonth: string) => {
  const { data } = await qaApi.get<MonthlySummaryRow[]>('/reports/monthly-summary', {
    params: { period_month: periodMonth },
  });
  return data;
};

export const getDashboard = async (periodMonth: string) => {
  const { data } = await qaApi.get<DashboardData>('/reports/dashboard', {
    params: { period_month: periodMonth },
  });
  return data;
};

export const getDynamics = async (
  fromMonth: string,
  toMonth: string,
  groupBy: 'direction' | 'species' | 'total' = 'direction'
) => {
  const { data } = await qaApi.get<DynamicsRow[]>('/reports/dynamics', {
    params: { from_month: fromMonth, to_month: toMonth, group_by: groupBy },
  });
  return data;
};

export const getHistory = async (
  speciesCode: string,
  directionCode: string,
  fromMonth?: string,
  toMonth?: string
) => {
  const { data } = await qaApi.get<HistoryEntry[]>('/reports/history', {
    params: {
      species_code: speciesCode,
      direction_code: directionCode,
      ...(fromMonth && { from_month: fromMonth }),
      ...(toMonth && { to_month: toMonth }),
    },
  });
  return data;
};

export const getVivariumGroups = async (periodMonth: string) => {
  const { data } = await qaApi.get<VivariumGroup[]>('/reports/vivarium-groups', {
    params: { period_month: periodMonth },
  });
  return data;
};

// ─── Экспорт ────────────────────────────────────────────────────────────────

export const downloadCsv = (periodMonth: string) => {
  const url = `/api/quarantine/export/csv?period_month=${encodeURIComponent(periodMonth)}`;
  const a = document.createElement('a');
  a.href = url;
  a.download = `quarantine_${periodMonth}.csv`;
  a.click();
};
