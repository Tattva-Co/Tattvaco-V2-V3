import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  api,
  type CameraProfileCreateBody,
  type CinematographyDecisionBody,
  type CinematographyOverrideBody,
  type CinematographyRecommendationBody,
  type CinematographyVersionProposeBody,
  type LensProfileCreateBody,
  type LightingProfileCreateBody,
} from "../api/client";

export function useCameraProfiles(projectId: string) {
  return useQuery({
    queryKey: ["camera-profiles", projectId],
    queryFn: () => api.cinematography.listCameraProfiles(projectId),
  });
}

export function useCreateCameraProfile(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CameraProfileCreateBody) => api.cinematography.createCameraProfile(projectId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["camera-profiles", projectId] }),
  });
}

export function useLensProfiles(projectId: string) {
  return useQuery({ queryKey: ["lens-profiles", projectId], queryFn: () => api.cinematography.listLensProfiles(projectId) });
}

export function useCreateLensProfile(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: LensProfileCreateBody) => api.cinematography.createLensProfile(projectId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["lens-profiles", projectId] }),
  });
}

export function useLightingProfiles(projectId: string) {
  return useQuery({
    queryKey: ["lighting-profiles", projectId],
    queryFn: () => api.cinematography.listLightingProfiles(projectId),
  });
}

export function useCreateLightingProfile(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: LightingProfileCreateBody) => api.cinematography.createLightingProfile(projectId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["lighting-profiles", projectId] }),
  });
}

export function useCurrentCinematographyBible(projectId: string) {
  return useQuery({
    queryKey: ["cinematography-bible-current", projectId],
    queryFn: () => api.cinematography.getCurrentBible(projectId),
  });
}

export function useCinematographyBibleVersions(projectId: string) {
  return useQuery({
    queryKey: ["cinematography-bible-versions", projectId],
    queryFn: () => api.cinematography.listBibleVersions(projectId),
  });
}

export function useProposeBibleVersion(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CinematographyVersionProposeBody) => api.cinematography.proposeBibleVersion(projectId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cinematography-bible-versions", projectId] }),
  });
}

export function useDecideBibleVersion(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ versionId, body }: { versionId: string; body: CinematographyDecisionBody }) =>
      api.cinematography.decideBibleVersion(projectId, versionId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cinematography-bible-versions", projectId] });
      queryClient.invalidateQueries({ queryKey: ["cinematography-bible-current", projectId] });
    },
  });
}

export function useCinematographyRecommendations(projectId: string) {
  return useQuery({
    queryKey: ["cinematography-recommendations", projectId],
    queryFn: () => api.cinematography.listRecommendations(projectId),
  });
}

export function useRequestRecommendation(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CinematographyRecommendationBody) => api.cinematography.requestRecommendation(projectId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cinematography-recommendations", projectId] }),
  });
}

export function useOverrideRecommendation(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ recommendationId, body }: { recommendationId: string; body: CinematographyOverrideBody }) =>
      api.cinematography.overrideRecommendation(projectId, recommendationId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cinematography-recommendations", projectId] }),
  });
}
