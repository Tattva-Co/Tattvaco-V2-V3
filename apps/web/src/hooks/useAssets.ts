import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

export function useAssets(projectId: string) {
  return useQuery({ queryKey: ["assets", projectId], queryFn: () => api.assets.list(projectId) });
}

export function useUploadAsset(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => api.assets.upload(projectId, file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["assets", projectId] }),
  });
}
