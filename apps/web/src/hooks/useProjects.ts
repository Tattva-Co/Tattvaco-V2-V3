import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  api,
  type EpisodeCreateBody,
  type OutputProfileCreateBody,
  type OutputProfileUpdateBody,
  type ProjectCreateBody,
  type ProjectMemberAddBody,
  type ProjectMemberRoleUpdateBody,
  type ProjectUpdateBody,
} from "../api/client";

export function useProjects(includeArchived = false) {
  return useQuery({
    queryKey: ["projects", { includeArchived }],
    queryFn: () => api.projects.list(includeArchived),
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

export function useUpdateProject(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ProjectUpdateBody) => api.projects.update(projectId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}

export function useArchiveProject(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (archived: boolean) =>
      archived ? api.projects.archive(projectId) : api.projects.unarchive(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}

export function useProjectSummary(projectId: string | undefined) {
  return useQuery({
    queryKey: ["projects", projectId, "summary"],
    queryFn: () => api.projects.summary(projectId!),
    enabled: Boolean(projectId),
  });
}

export function useProjectTemplates() {
  return useQuery({
    queryKey: ["project-templates"],
    queryFn: api.projectTemplates.list,
    staleTime: Infinity, // a fixed, code-defined catalogue -- never changes mid-session
  });
}

export function useOutputProfiles(projectId: string | undefined) {
  return useQuery({
    queryKey: ["projects", projectId, "output-profiles"],
    queryFn: () => api.outputProfiles.list(projectId!),
    enabled: Boolean(projectId),
  });
}

export function useCreateOutputProfile(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: OutputProfileCreateBody) => api.outputProfiles.create(projectId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "output-profiles"] });
    },
  });
}

export function useUpdateOutputProfile(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ profileId, body }: { profileId: string; body: OutputProfileUpdateBody }) =>
      api.outputProfiles.update(projectId, profileId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "output-profiles"] });
    },
  });
}

export function useDeleteOutputProfile(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (profileId: string) => api.outputProfiles.delete(projectId, profileId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "output-profiles"] });
    },
  });
}

export function useEpisodes(projectId: string | undefined) {
  return useQuery({
    queryKey: ["projects", projectId, "episodes"],
    queryFn: () => api.episodes.list(projectId!),
    enabled: Boolean(projectId),
  });
}

export function useCreateEpisode(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: EpisodeCreateBody) => api.episodes.create(projectId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "episodes"] });
    },
  });
}

export function useRoleTemplates(projectId: string | undefined) {
  return useQuery({
    queryKey: ["projects", projectId, "role-templates"],
    queryFn: () => api.members.roleTemplates(projectId!),
    enabled: Boolean(projectId),
  });
}

export function useProjectMembers(projectId: string | undefined) {
  return useQuery({
    queryKey: ["projects", projectId, "members"],
    queryFn: () => api.members.list(projectId!),
    enabled: Boolean(projectId),
  });
}

export function useAddProjectMember(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ProjectMemberAddBody) => api.members.add(projectId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "members"] });
    },
  });
}

export function useUpdateProjectMemberRole(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, body }: { userId: string; body: ProjectMemberRoleUpdateBody }) =>
      api.members.updateRole(projectId, userId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "members"] });
    },
  });
}

export function useRemoveProjectMember(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => api.members.remove(projectId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "members"] });
    },
  });
}
