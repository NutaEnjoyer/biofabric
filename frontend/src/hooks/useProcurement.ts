import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as prApi from '../api/procurement';
import type { ProcurementCreate, ProcurementStatus, ApprovalIn, SupplierQuoteIn, DocumentIn } from '../types/procurement';

// Queries
export const useRequests = (status?: ProcurementStatus) => {
  return useQuery({
    queryKey: ['procurement', 'requests', status],
    queryFn: () => prApi.getRequests(status),
  });
};

export const useRequest = (id: number) => {
  return useQuery({
    queryKey: ['procurement', 'request', id],
    queryFn: () => prApi.getRequest(id),
    enabled: !!id,
  });
};

export const useQuotes = (requestId: number) => {
  return useQuery({
    queryKey: ['procurement', 'quotes', requestId],
    queryFn: () => prApi.getQuotes(requestId),
    enabled: !!requestId,
  });
};

export const useDocuments = (requestId: number) => {
  return useQuery({
    queryKey: ['procurement', 'documents', requestId],
    queryFn: () => prApi.getDocuments(requestId),
    enabled: !!requestId,
  });
};

// Mutations
export const useCreateRequest = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProcurementCreate) => prApi.createRequest(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['procurement', 'requests'] });
    },
  });
};

export const usePatchStatus = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id: number; status: ProcurementStatus }) => prApi.patchStatus(vars),
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: ['procurement', 'requests'] });
      queryClient.invalidateQueries({ queryKey: ['procurement', 'request', vars.id] });
    },
  });
};

export const useAddApproval = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ApprovalIn) => prApi.addApproval(payload),
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: ['procurement', 'request', vars.request_id] });
    },
  });
};

export const useAddQuote = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SupplierQuoteIn) => prApi.addQuote(payload),
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: ['procurement', 'quotes', vars.request_id] });
    },
  });
};

export const useAddDocument = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: DocumentIn) => prApi.addDocument(payload),
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: ['procurement', 'documents', vars.request_id] });
    },
  });
};
