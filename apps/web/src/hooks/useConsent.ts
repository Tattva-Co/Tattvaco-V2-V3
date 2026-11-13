import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  api,
  type ConsentCreateBody,
  type ConsentDecisionBody,
  type ConsentRevokeBody,
  type PerformerCreateBody,
  type VoiceProfileCreateBody,
} from "../api/client";

export function usePerformers(projectId: string) {
  return useQuery({ queryKey: ["performers", projectId], queryFn: () => api.performers.list(projectId) });
}

export function useCreatePerformer(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: PerformerCreateBody) => api.performers.create(projectId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["performers", projectId] }),
  });
}

export function usePerformerConsents(projectId: string, performerId: string) {
  return useQuery({
    queryKey: ["performer-consents", projectId, performerId],
    queryFn: () => api.performers.listConsents(projectId, performerId),
    enabled: !!performerId,
  });
}

export function useCreateConsent(projectId: string, performerId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ConsentCreateBody) => api.performers.createConsent(projectId, performerId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["performer-consents", projectId, performerId] }),
  });
}

export function useDecideConsent(projectId: string, performerId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ consentId, body }: { consentId: string; body: ConsentDecisionBody }) =>
      api.consent.decide(projectId, consentId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["performer-consents", projectId, performerId] }),
  });
}

export function useRevokeConsent(projectId: string, performerId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ConsentRevokeBody) => api.consent.revoke(projectId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["performer-consents", projectId, performerId] }),
  });
}

export function useVoiceProfiles(projectId: string) {
  return useQuery({ queryKey: ["voice-profiles", projectId], queryFn: () => api.voiceProfiles.list(projectId) });
}

export function useCreateVoiceProfile(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: VoiceProfileCreateBody) => api.voiceProfiles.create(projectId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["voice-profiles", projectId] }),
  });
}
