import axios from 'axios';
import type {
  ProcurementRequest,
  ProcurementCreate,
  ProcurementStatus,
  ApprovalIn,
  SupplierQuoteIn,
  DocumentIn,
  SupplierQuote,
  ProcurementDocument,
} from '../types/procurement';

// nginx proxies /api/procurement/* → tz_procurement_proof service
const prApi = axios.create({
  baseURL: '/api/procurement',
  headers: { 'Content-Type': 'application/json' },
});

prApi.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail || err.message || 'Ошибка сервера';
    console.error('Procurement API Error:', msg);
    return Promise.reject(err);
  }
);

// Requests
export const getRequests = async (status?: ProcurementStatus) => {
  const { data } = await prApi.get<ProcurementRequest[]>('/requests', {
    params: status ? { status } : undefined,
  });
  return data;
};

export const getRequest = async (id: number) => {
  const { data } = await prApi.get<ProcurementRequest>(`/requests/${id}`);
  return data;
};

export const createRequest = async (payload: ProcurementCreate) => {
  const { data } = await prApi.post<ProcurementRequest>('/requests', payload);
  return data;
};

export const patchStatus = async ({ id, status }: { id: number; status: ProcurementStatus }) => {
  const { data } = await prApi.patch<ProcurementRequest>(`/requests/${id}/status`, { status });
  return data;
};

// Approvals
export const addApproval = async (payload: ApprovalIn) => {
  const { data } = await prApi.post<{ ok: boolean }>('/approvals', payload);
  return data;
};

// Supplier quotes
export const getQuotes = async (requestId: number) => {
  const { data } = await prApi.get<SupplierQuote[]>(`/suppliers/quotes/${requestId}`);
  return data;
};

export const addQuote = async (payload: SupplierQuoteIn) => {
  const { data } = await prApi.post<{ ok: boolean; quote_id: number }>('/suppliers/quotes', payload);
  return data;
};

// Documents
export const getDocuments = async (requestId: number) => {
  const { data } = await prApi.get<ProcurementDocument[]>(`/documents/${requestId}`);
  return data;
};

export const addDocument = async (payload: DocumentIn) => {
  const { data } = await prApi.post<{ ok: boolean; document_id: number }>('/documents', payload);
  return data;
};
