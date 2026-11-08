import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type ProjectCreateBody } from "../api/client";

export function useProjects() {
  return useQuery({
    queryKey: ["projects"],
    queryFn: api.projects.list,
  });
}

export function useProject(projectId: string | undefined) {
  return useQuery({
    queryKey: ["projects", projectId],
    queryFn: () => api.projects.get(projectId!),
    enabled: Boolean(projectId),
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ProjectCreateBody) => api.projects.create(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}
