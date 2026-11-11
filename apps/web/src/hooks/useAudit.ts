import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

export function useAuditLog(projectId: string) {
  return useQuery({ queryKey: ["audit-log", projectId], queryFn: () => api.projects.auditLog(projectId) });
}
