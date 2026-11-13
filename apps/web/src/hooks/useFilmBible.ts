import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type FilmBibleRuleCreateBody } from "../api/client";

export function useFilmBibleRules(projectId: string) {
  return useQuery({ queryKey: ["film-bible-rules", projectId], queryFn: () => api.filmBible.rules.list(projectId) });
}

export function useCreateFilmBibleRule(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: FilmBibleRuleCreateBody) => api.filmBible.rules.create(projectId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["film-bible-rules", projectId] }),
  });
}

export function useScenes(projectId: string) {
  return useQuery({ queryKey: ["scenes", projectId], queryFn: () => api.projects.scenes(projectId) });
}

export function useEntities(projectId: string) {
  return useQuery({ queryKey: ["entities", projectId], queryFn: () => api.projects.entities(projectId) });
}

export function useDialogueSegments(projectId: string) {
  return useQuery({
    queryKey: ["dialogue-segments", projectId],
    queryFn: () => api.projects.dialogueSegments(projectId),
  });
}

export function useCharacters(projectId: string) {
  return useQuery({ queryKey: ["characters", projectId], queryFn: () => api.projects.characters(projectId) });
}

export function useLocations(projectId: string) {
  return useQuery({ queryKey: ["locations", projectId], queryFn: () => api.projects.locations(projectId) });
}

export function useProjectVersions(projectId: string) {
  return useQuery({ queryKey: ["project-versions", projectId], queryFn: () => api.projects.versions(projectId) });
}
