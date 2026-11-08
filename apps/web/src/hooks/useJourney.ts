import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type JourneyItemAction } from "../api/client";

export function useJourney(projectId: string | undefined) {
  return useQuery({
    queryKey: ["journey", projectId],
    queryFn: () => api.journey.get(projectId!),
    enabled: Boolean(projectId),
  });
}

export function useActOnJourneyItem(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ jrnId, action }: { jrnId: string; action: JourneyItemAction }) =>
      api.journey.actOnItem(projectId, jrnId, action),
    onSuccess: () => {
      // Re-fetch the whole journey rather than patch the cache locally: a single
      // subpoint action can change its group's status, its section's status, AND (via
      // the system-check cache) another group's derived status in the same response --
      // deriving that client-side would duplicate packages/domain/journey.py's logic.
      queryClient.invalidateQueries({ queryKey: ["journey", projectId] });
    },
  });
}

export function useContinueSection(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jrnSectionId: string) => api.journey.continueSection(projectId, jrnSectionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["journey", projectId] });
    },
  });
}
