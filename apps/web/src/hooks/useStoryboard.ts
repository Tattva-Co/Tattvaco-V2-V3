import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type StoryboardIngestBody, type StoryboardMappingCreateBody } from "../api/client";

export function useStoryboardPanels(projectId: string) {
  return useQuery({ queryKey: ["storyboard-panels", projectId], queryFn: () => api.storyboard.panels(projectId) });
}

export function useIngestStoryboard(projectId: string) {
  return useMutation({
    mutationFn: (body: StoryboardIngestBody) => api.storyboard.ingest(projectId, body),
  });
}

export function useStoryboardMappings(projectId: string) {
  return useQuery({
    queryKey: ["storyboard-mappings", projectId],
    queryFn: () => api.storyboard.listMappings(projectId),
  });
}

export function useCreateStoryboardMapping(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: StoryboardMappingCreateBody) => api.storyboard.createMapping(projectId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["storyboard-mappings", projectId] }),
  });
}
