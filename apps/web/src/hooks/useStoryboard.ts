import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

export function useStoryboardPanels(projectId: string) {
  return useQuery({ queryKey: ["storyboard-panels", projectId], queryFn: () => api.storyboard.panels(projectId) });
}
