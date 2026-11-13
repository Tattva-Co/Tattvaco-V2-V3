import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  api,
  type CharacterDecisionBody,
  type CharacterFacialReferenceCreateBody,
  type CharacterStateCreateBody,
  type CharacterVersionProposeBody,
  type MeasurementCorrectBody,
  type MeasurementCreateBody,
} from "../api/client";

export function useCharacterDetail(projectId: string, characterId: string) {
  return useQuery({
    queryKey: ["character-detail", projectId, characterId],
    queryFn: () => api.characters.get(projectId, characterId),
    enabled: !!characterId,
  });
}

export function useCharacterVersions(projectId: string, characterId: string) {
  return useQuery({
    queryKey: ["character-versions", projectId, characterId],
    queryFn: () => api.characters.listVersions(projectId, characterId),
    enabled: !!characterId,
  });
}

export function useProposeCharacterVersion(projectId: string, characterId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CharacterVersionProposeBody) => api.characters.proposeVersion(projectId, characterId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["character-versions", projectId, characterId] });
    },
  });
}

export function useDecideCharacterVersion(projectId: string, characterId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ versionId, body }: { versionId: string; body: CharacterDecisionBody }) =>
      api.characters.decideVersion(projectId, characterId, versionId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["character-versions", projectId, characterId] });
      queryClient.invalidateQueries({ queryKey: ["character-detail", projectId, characterId] });
    },
  });
}

export function useFacialReferences(projectId: string, characterId: string) {
  return useQuery({
    queryKey: ["facial-references", projectId, characterId],
    queryFn: () => api.characters.listFacialReferences(projectId, characterId),
    enabled: !!characterId,
  });
}

export function useAddFacialReference(projectId: string, characterId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CharacterFacialReferenceCreateBody) => api.characters.addFacialReference(projectId, characterId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["facial-references", projectId, characterId] }),
  });
}

export function useCharacterStates(projectId: string, characterId: string) {
  return useQuery({
    queryKey: ["character-states", projectId, characterId],
    queryFn: () => api.characters.listStates(projectId, characterId),
    enabled: !!characterId,
  });
}

export function useCreateCharacterState(projectId: string, characterId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CharacterStateCreateBody) => api.characters.createState(projectId, characterId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["character-states", projectId, characterId] }),
  });
}

export function useMeasurementHistory(projectId: string, subjectType: string, subjectId: string) {
  return useQuery({
    queryKey: ["measurements", projectId, subjectType, subjectId],
    queryFn: () => api.measurements.history(projectId, subjectType, subjectId),
    enabled: !!subjectId,
  });
}

export function useSaveMeasurement(projectId: string, subjectType: string, subjectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: MeasurementCreateBody) => api.measurements.save(projectId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["measurements", projectId, subjectType, subjectId] }),
  });
}

export function useCorrectMeasurement(projectId: string, subjectType: string, subjectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ measurementId, body }: { measurementId: string; body: MeasurementCorrectBody }) =>
      api.measurements.correct(projectId, measurementId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["measurements", projectId, subjectType, subjectId] }),
  });
}

export function useVerifyMeasurement(projectId: string, subjectType: string, subjectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (measurementId: string) => api.measurements.verify(projectId, measurementId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["measurements", projectId, subjectType, subjectId] }),
  });
}
