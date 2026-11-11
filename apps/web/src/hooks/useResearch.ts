import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type ResearchQuestionCreateBody, type ResearchSourceCreateBody } from "../api/client";

export function useResearchQuestions(projectId: string) {
  return useQuery({ queryKey: ["research-questions", projectId], queryFn: () => api.research.questions.list(projectId) });
}

export function useCreateResearchQuestion(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ResearchQuestionCreateBody) => api.research.questions.create(projectId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["research-questions", projectId] }),
  });
}

export function useResearchSources(projectId: string) {
  return useQuery({ queryKey: ["research-sources", projectId], queryFn: () => api.research.sources.list(projectId) });
}

export function useCreateResearchSource(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ResearchSourceCreateBody) => api.research.sources.create(projectId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["research-sources", projectId] }),
  });
}

export function useResearchClaims(projectId: string) {
  return useQuery({ queryKey: ["research-claims", projectId], queryFn: () => api.research.claims.list(projectId) });
}

export function useResearchConflicts(projectId: string) {
  return useQuery({ queryKey: ["research-conflicts", projectId], queryFn: () => api.research.conflicts.list(projectId) });
}
