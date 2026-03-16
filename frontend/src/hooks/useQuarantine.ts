import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as qaApi from '../api/quarantine';
import type { OperationCreate } from '../types/quarantine';

// ─── Справочники ────────────────────────────────────────────────────────────

export const useSpecies = () =>
  useQuery({ queryKey: ['quarantine', 'species'], queryFn: qaApi.getSpecies });

export const useDirections = () =>
  useQuery({ queryKey: ['quarantine', 'directions'], queryFn: qaApi.getDirections });

export const useAgeCategories = (speciesCode: string) =>
  useQuery({
    queryKey: ['quarantine', 'age-categories', speciesCode],
    queryFn: () => qaApi.getAgeCategories(speciesCode),
    enabled: !!speciesCode,
  });

export const useMassBins = (speciesCode: string) =>
  useQuery({
    queryKey: ['quarantine', 'mass-bins', speciesCode],
    queryFn: () => qaApi.getMassBins(speciesCode),
    enabled: !!speciesCode,
  });

export const useGroups = () =>
  useQuery({ queryKey: ['quarantine', 'groups'], queryFn: qaApi.getGroups });

export const useCohorts = () =>
  useQuery({ queryKey: ['quarantine', 'cohorts'], queryFn: qaApi.getCohorts });

// ─── Операции ───────────────────────────────────────────────────────────────

export const useCreateOperation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: OperationCreate) => qaApi.createOperation(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['quarantine'] }),
  });
};

export const useConfirmOperation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (entryId: number) => qaApi.confirmOperation(entryId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['quarantine'] }),
  });
};

export const useImportCsv = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => qaApi.importCsv(file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['quarantine'] }),
  });
};

// ─── Отчёты ─────────────────────────────────────────────────────────────────

export const useMonthlySummary = (periodMonth: string) =>
  useQuery({
    queryKey: ['quarantine', 'monthly-summary', periodMonth],
    queryFn: () => qaApi.getMonthlySummary(periodMonth),
    enabled: !!periodMonth,
  });

export const useDashboard = (periodMonth: string) =>
  useQuery({
    queryKey: ['quarantine', 'dashboard', periodMonth],
    queryFn: () => qaApi.getDashboard(periodMonth),
    enabled: !!periodMonth,
  });

export const useDynamics = (
  fromMonth: string,
  toMonth: string,
  groupBy: 'direction' | 'species' | 'total' = 'direction'
) =>
  useQuery({
    queryKey: ['quarantine', 'dynamics', fromMonth, toMonth, groupBy],
    queryFn: () => qaApi.getDynamics(fromMonth, toMonth, groupBy),
    enabled: !!fromMonth && !!toMonth,
  });

export const useHistory = (
  speciesCode: string,
  directionCode: string,
  fromMonth?: string,
  toMonth?: string
) =>
  useQuery({
    queryKey: ['quarantine', 'history', speciesCode, directionCode, fromMonth, toMonth],
    queryFn: () => qaApi.getHistory(speciesCode, directionCode, fromMonth, toMonth),
    enabled: !!speciesCode && !!directionCode,
  });

export const useVivariumGroups = (periodMonth: string) =>
  useQuery({
    queryKey: ['quarantine', 'vivarium-groups', periodMonth],
    queryFn: () => qaApi.getVivariumGroups(periodMonth),
    enabled: !!periodMonth,
  });
