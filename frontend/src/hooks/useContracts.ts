import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as contractsApi from '../api/contracts';

// Queries
export const useContracts = (params?: { status_code?: string; limit?: number; offset?: number }) => {
  return useQuery({
    queryKey: ['contracts', params],
    queryFn: () => contractsApi.getContracts(params),
  });
};

export const useContract = (id: number) => {
  return useQuery({
    queryKey: ['contract', id],
    queryFn: () => contractsApi.getContract(id),
    enabled: !!id,
  });
};

export const useContractsWithoutGuarantee = () => {
  return useQuery({
    queryKey: ['contracts', 'without-guarantee'],
    queryFn: contractsApi.getContractsWithoutGuarantee,
  });
};

export const useGuaranteeShare = () => {
  return useQuery({
    queryKey: ['kpi', 'guarantee-share'],
    queryFn: contractsApi.getGuaranteeShare,
  });
};

export const useIssues = (minSeverity?: number) => {
  return useQuery({
    queryKey: ['kpi', 'issues', minSeverity],
    queryFn: () => contractsApi.getIssues(minSeverity),
  });
};

// Mutations
export const useBindWorkflow = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: contractsApi.bindWorkflow,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contracts'] });
    },
  });
};

export const useSyncDeadlines = () => {
  return useMutation({
    mutationFn: contractsApi.syncDeadlines,
  });
};

export const useMarkOverdue = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: contractsApi.markOverdue,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contracts'] });
    },
  });
};

export const useValidateParties = () => {
  return useMutation({
    mutationFn: contractsApi.validateParties,
  });
};

export const useSendNotification = () => {
  return useMutation({
    mutationFn: contractsApi.sendNotification,
  });
};

export const useEnqueueEIS = () => {
  return useMutation({
    mutationFn: contractsApi.enqueueEIS,
  });
};

export const useStage1C = () => {
  return useMutation({
    mutationFn: contractsApi.stage1C,
  });
};

export const useUpsert1C = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: contractsApi.upsert1C,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contracts'] });
    },
  });
};

// ─── Таймлайн ────────────────────────────────────────────────────────────────

export const useContractTimeline = (contractId: number) => {
  return useQuery({
    queryKey: ['contract', contractId, 'timeline'],
    queryFn: () => contractsApi.getTimeline(contractId),
    enabled: !!contractId,
  });
};

// ─── ИИ-анализ ───────────────────────────────────────────────────────────────

export const useContractAIAnalysis = (contractId: number) => {
  return useQuery({
    queryKey: ['contract', contractId, 'ai-analysis'],
    queryFn: () => contractsApi.getAIAnalysis(contractId),
    enabled: !!contractId,
  });
};

export const useStartAIAnalysis = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: contractsApi.startAIAnalysis,
    onSuccess: (_, contractId) => {
      queryClient.invalidateQueries({ queryKey: ['contract', contractId, 'ai-analysis'] });
    },
  });
};

// ─── Отправка в 1С ───────────────────────────────────────────────────────────

export const useSendTo1C = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: contractsApi.sendTo1C,
    onSuccess: (_, contractId) => {
      queryClient.invalidateQueries({ queryKey: ['contract', contractId] });
    },
  });
};
