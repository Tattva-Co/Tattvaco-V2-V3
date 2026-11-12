import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  api,
  type ScreenplayDecisionBody,
  type ScreenplaySuggestionDecisionBody,
  type ScreenplaySuggestionGenerateBody,
  type ScreenplayVersionImportBody,
  type ScreenplayVersionUpdateBody,
} from "../api/client";

export function useScreenplayVersions(projectId: string | undefined) {
  return useQuery({
    queryKey: ["projects", projectId, "screenplay-versions"],
    queryFn: () => api.screenplay.listVersions(projectId!),
    enabled: Boolean(projectId),
  });
}

export function useScreenplayVersion(projectId: string | undefined, versionId: string | undefined) {
  return useQuery({
    queryKey: ["projects", projectId, "screenplay-versions", versionId],
    queryFn: () => api.screenplay.getVersion(projectId!, versionId!),
    enabled: Boolean(projectId && versionId),
  });
}

export function useImportScreenplayVersion(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ScreenplayVersionImportBody) => api.screenplay.importVersion(projectId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "screenplay-versions"] });
    },
  });
}

export function useUpdateScreenplayVersion(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ versionId, body }: { versionId: string; body: ScreenplayVersionUpdateBody }) =>
      api.screenplay.updateVersion(projectId, versionId, body),
    onSuccess: (_, { versionId }) => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "screenplay-versions"] });
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "screenplay-versions", versionId] });
    },
  });
}

export function useScreenplayDiff(projectId: string | undefined, versionId: string | undefined, against: string | undefined) {
  return useQuery({
    queryKey: ["projects", projectId, "screenplay-versions", versionId, "diff", against],
    queryFn: () => api.screenplay.diff(projectId!, versionId!, against!),
    enabled: Boolean(projectId && versionId && against),
  });
}

export function useReviseScreenplay(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (baseVersionId: string) => api.screenplay.revise(projectId, baseVersionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "screenplay-versions"] });
    },
  });
}

export function useSubmitScreenplayRevision(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ versionId, justification }: { versionId: string; justification: string }) =>
      api.screenplay.submit(projectId, versionId, justification),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "screenplay-versions"] });
    },
  });
}

export function useDecideScreenplayRevision(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ versionId, body }: { versionId: string; body: ScreenplayDecisionBody }) =>
      api.screenplay.decide(projectId, versionId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "screenplay-versions"] });
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "impact-analyses"] });
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "scenes"] });
    },
  });
}

export function useConfirmLegacyLock(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (versionId: string) => api.screenplay.confirmLegacyLock(projectId, versionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "screenplay-versions"] });
    },
  });
}

export function useImpactPreview(projectId: string | undefined, versionId: string | undefined) {
  return useQuery({
    queryKey: ["projects", projectId, "screenplay-versions", versionId, "impact-preview"],
    queryFn: () => api.screenplay.previewImpact(projectId!, versionId!),
    enabled: Boolean(projectId && versionId),
  });
}

export function useScreenplaySuggestions(projectId: string | undefined, versionId: string | undefined) {
  return useQuery({
    queryKey: ["projects", projectId, "screenplay-versions", versionId, "suggestions"],
    queryFn: () => api.screenplay.listSuggestions(projectId!, versionId!),
    enabled: Boolean(projectId && versionId),
  });
}

export function useGenerateScreenplaySuggestions(projectId: string, versionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ScreenplaySuggestionGenerateBody) => api.screenplay.generateSuggestions(projectId, versionId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "screenplay-versions", versionId, "suggestions"] });
    },
  });
}

export function useDecideScreenplaySuggestion(projectId: string, versionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ suggestionId, body }: { suggestionId: string; body: ScreenplaySuggestionDecisionBody }) =>
      api.screenplay.decideSuggestion(projectId, suggestionId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "screenplay-versions", versionId, "suggestions"] });
    },
  });
}

export function useImpactAnalyses(projectId: string | undefined) {
  return useQuery({
    queryKey: ["projects", projectId, "impact-analyses"],
    queryFn: () => api.screenplay.listImpactAnalyses(projectId!),
    enabled: Boolean(projectId),
  });
}
