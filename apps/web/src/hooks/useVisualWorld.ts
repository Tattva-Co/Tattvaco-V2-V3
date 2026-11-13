import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  api,
  type CostumeAssignmentCreateBody,
  type CostumeCreateBody,
  type CostumeDecisionBody,
  type CostumeStateCreateBody,
  type CostumeVersionProposeBody,
  type EnvironmentStateCreateBody,
  type LocationDecisionBody,
  type LocationVersionProposeBody,
  type PropCreateBody,
  type PropStateCreateBody,
} from "../api/client";

// -- Locations & environment states --------------------------------------------------

export function useLocationDetail(projectId: string, locationId: string) {
  return useQuery({
    queryKey: ["location-detail", projectId, locationId],
    queryFn: () => api.locations.get(projectId, locationId),
    enabled: !!locationId,
  });
}

export function useLocationVersions(projectId: string, locationId: string) {
  return useQuery({
    queryKey: ["location-versions", projectId, locationId],
    queryFn: () => api.locations.listVersions(projectId, locationId),
    enabled: !!locationId,
  });
}

export function useProposeLocationVersion(projectId: string, locationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: LocationVersionProposeBody) => api.locations.proposeVersion(projectId, locationId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["location-versions", projectId, locationId] }),
  });
}

export function useDecideLocationVersion(projectId: string, locationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ versionId, body }: { versionId: string; body: LocationDecisionBody }) =>
      api.locations.decideVersion(projectId, locationId, versionId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["location-versions", projectId, locationId] });
      queryClient.invalidateQueries({ queryKey: ["location-detail", projectId, locationId] });
    },
  });
}

export function useAdoptLocation(projectId: string) {
  return useMutation({
    mutationFn: (locationId: string) => api.locations.adopt(projectId, locationId),
  });
}

export function useEnvironmentState(projectId: string, sceneId: string) {
  return useQuery({
    queryKey: ["environment-state", projectId, sceneId],
    queryFn: () => api.environmentStates.current(projectId, sceneId),
    enabled: !!sceneId,
  });
}

export function useCreateEnvironmentState(projectId: string, sceneId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: EnvironmentStateCreateBody) => api.environmentStates.create(projectId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["environment-state", projectId, sceneId] }),
  });
}

// -- Costumes -------------------------------------------------------------------------

export function useCostumes(projectId: string) {
  return useQuery({ queryKey: ["costumes", projectId], queryFn: () => api.costumes.list(projectId) });
}

export function useCreateCostume(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CostumeCreateBody) => api.costumes.create(projectId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["costumes", projectId] }),
  });
}

export function useCostumeDetail(projectId: string, costumeId: string) {
  return useQuery({
    queryKey: ["costume-detail", projectId, costumeId],
    queryFn: () => api.costumes.get(projectId, costumeId),
    enabled: !!costumeId,
  });
}

export function useCostumeVersions(projectId: string, costumeId: string) {
  return useQuery({
    queryKey: ["costume-versions", projectId, costumeId],
    queryFn: () => api.costumes.listVersions(projectId, costumeId),
    enabled: !!costumeId,
  });
}

export function useProposeCostumeVersion(projectId: string, costumeId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CostumeVersionProposeBody) => api.costumes.proposeVersion(projectId, costumeId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["costume-versions", projectId, costumeId] }),
  });
}

export function useDecideCostumeVersion(projectId: string, costumeId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ versionId, body }: { versionId: string; body: CostumeDecisionBody }) =>
      api.costumes.decideVersion(projectId, costumeId, versionId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["costume-versions", projectId, costumeId] });
      queryClient.invalidateQueries({ queryKey: ["costume-detail", projectId, costumeId] });
    },
  });
}

export function useCostumeStates(projectId: string, costumeId: string) {
  return useQuery({
    queryKey: ["costume-states", projectId, costumeId],
    queryFn: () => api.costumes.listStates(projectId, costumeId),
    enabled: !!costumeId,
  });
}

export function useCreateCostumeState(projectId: string, costumeId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CostumeStateCreateBody) => api.costumes.createState(projectId, costumeId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["costume-states", projectId, costumeId] }),
  });
}

export function useCreateCostumeAssignment(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CostumeAssignmentCreateBody) => api.costumeAssignments.create(projectId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["continuity-findings", projectId] }),
  });
}

export function useContinuityFindings(projectId: string) {
  return useQuery({
    queryKey: ["continuity-findings", projectId],
    queryFn: () => api.continuityFindings.list(projectId),
  });
}

// -- Props & weapons --------------------------------------------------------------------

export function useProps(projectId: string) {
  return useQuery({ queryKey: ["props", projectId], queryFn: () => api.props.list(projectId) });
}

export function useCreateProp(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: PropCreateBody) => api.props.create(projectId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["props", projectId] }),
  });
}

export function usePropStates(projectId: string, propId: string) {
  return useQuery({
    queryKey: ["prop-states", projectId, propId],
    queryFn: () => api.props.listStates(projectId, propId),
    enabled: !!propId,
  });
}

export function useCreatePropState(projectId: string, propId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: PropStateCreateBody) => api.props.createState(projectId, propId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["prop-states", projectId, propId] }),
  });
}
