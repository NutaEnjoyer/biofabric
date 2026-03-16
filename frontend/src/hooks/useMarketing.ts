import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as mk from '../api/marketing';

// ─── Posts ────────────────────────────────────────────────────────────────────

export const usePosts = (params?: { period_from?: string; period_to?: string }) =>
  useQuery({ queryKey: ['mk', 'posts', params], queryFn: () => mk.getPosts(params) });

export const usePost = (id: number) =>
  useQuery({ queryKey: ['mk', 'post', id], queryFn: () => mk.getPost(id), enabled: !!id });

export const useCreatePost = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: mk.createPost,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mk', 'posts'] }),
  });
};

export const useUpdatePost = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: mk.updatePost,
    onSuccess: (_d, vars) => {
      qc.invalidateQueries({ queryKey: ['mk', 'post', vars.id] });
      qc.invalidateQueries({ queryKey: ['mk', 'posts'] });
    },
  });
};

export const useSetPostStatus = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: mk.setPostStatus,
    onSuccess: (_d, vars) => {
      qc.invalidateQueries({ queryKey: ['mk', 'post', vars.id] });
      qc.invalidateQueries({ queryKey: ['mk', 'posts'] });
      qc.invalidateQueries({ queryKey: ['mk', 'calendar'] });
    },
  });
};

export const useSetPostDate = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: mk.setPostDate,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['mk', 'posts'] });
      qc.invalidateQueries({ queryKey: ['mk', 'calendar'] });
      qc.invalidateQueries({ queryKey: ['mk', 'ideas'] });
    },
  });
};

export const usePublishPost = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: mk.publishPost,
    onSuccess: (_d, vars) => qc.invalidateQueries({ queryKey: ['mk', 'post', vars.id] }),
  });
};

export const useReplacePost = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: mk.replacePost,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['mk', 'calendar'] });
      qc.invalidateQueries({ queryKey: ['mk', 'ideas'] });
    },
  });
};

// ─── Calendar ─────────────────────────────────────────────────────────────────

export const useCalendar = (params?: { period_from?: string; period_to?: string }) =>
  useQuery({ queryKey: ['mk', 'calendar', params], queryFn: () => mk.getCalendar(params) });

export const useIdeas = () =>
  useQuery({ queryKey: ['mk', 'ideas'], queryFn: mk.getIdeas });

// ─── Sources ──────────────────────────────────────────────────────────────────

export const useSources = () =>
  useQuery({ queryKey: ['mk', 'sources'], queryFn: mk.getSources });

export const useCreateSource = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: mk.createSource,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mk', 'sources'] }),
  });
};

export const useDeleteSource = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: mk.deleteSource,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mk', 'sources'] }),
  });
};

// ─── AI ───────────────────────────────────────────────────────────────────────

export const useAIGeneratePlan = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: mk.aiGeneratePlan,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mk', 'ideas'] }),
  });
};

export const useAIGenerateIdeas = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: mk.aiGenerateIdeas,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mk', 'ideas'] }),
  });
};

// Генерация текста для конкретного поста — не инвалидирует, только возвращает предложение
export const useAIGeneratePostText = () =>
  useMutation({ mutationFn: mk.aiGeneratePostText });

// Рерайт текста поста — не инвалидирует, только возвращает предложение
export const useAIRewritePost = () =>
  useMutation({ mutationFn: mk.aiRewritePost });

// ─── Plan Jobs ────────────────────────────────────────────────────────────────

export const usePlanJobs = () =>
  useQuery({ queryKey: ['mk', 'plan-jobs'], queryFn: mk.getPlanJobs });

export const useCreatePlanJob = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: mk.createPlanJob,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['mk', 'plan-jobs'] });
      qc.invalidateQueries({ queryKey: ['mk', 'ideas'] });
    },
  });
};

// ─── Analytics ────────────────────────────────────────────────────────────────

export const useAnalyticsByChannel = () =>
  useQuery({ queryKey: ['mk', 'analytics', 'by-channel'], queryFn: mk.getAnalyticsByChannel });

export const useAnalyticsByTopic = () =>
  useQuery({ queryKey: ['mk', 'analytics', 'by-topic'], queryFn: mk.getAnalyticsByTopic });

export const useAnalyticsByFormat = () =>
  useQuery({ queryKey: ['mk', 'analytics', 'by-format'], queryFn: mk.getAnalyticsByFormat });

export const useAnalyticsDensity = () =>
  useQuery({ queryKey: ['mk', 'analytics', 'density'], queryFn: mk.getAnalyticsDensity });

export const useAnalyticsGaps = () =>
  useQuery({ queryKey: ['mk', 'analytics', 'gaps'], queryFn: mk.getAnalyticsGaps });

export const useNotifyUpcoming = () =>
  useMutation({ mutationFn: mk.notifyUpcoming });

export const useAnalyticsWarnings = () =>
  useQuery({ queryKey: ['mk', 'analytics', 'warnings'], queryFn: mk.getAnalyticsWarnings });
