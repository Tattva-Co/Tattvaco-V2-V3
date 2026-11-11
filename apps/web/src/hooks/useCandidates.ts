import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type ApprovalDecisionBody } from "../api/client";

export function useCandidates(projectId: string) {
  return useQuery({ queryKey: ["candidates", projectId], queryFn: () => api.candidates.get(projectId) });
}

/** Approving/rejecting changes the project's canonical scenes/entities/claims/etc, not
 * just the candidates list -- every view that reads canonical state is invalidated
 * alongside the candidates query itself, so an approval is reflected everywhere at once
 * (the Film Bible tool's scene/entity tabs, the journey's system-derived checks, etc). */
export function useDecideApproval(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ approvalId, body }: { approvalId: string; body: ApprovalDecisionBody }) =>
      api.approvals.decide(approvalId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["candidates", projectId] });
      queryClient.invalidateQueries({ queryKey: ["scenes", projectId] });
      queryClient.invalidateQueries({ queryKey: ["entities", projectId] });
      queryClient.invalidateQueries({ queryKey: ["research-claims", projectId] });
      queryClient.invalidateQueries({ queryKey: ["research-questions", projectId] });
      queryClient.invalidateQueries({ queryKey: ["storyboard-panels", projectId] });
      queryClient.invalidateQueries({ queryKey: ["film-bible-rules", projectId] });
      queryClient.invalidateQueries({ queryKey: ["journey", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects", projectId] });
    },
  });
}
