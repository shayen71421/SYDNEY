"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "./api";

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: api.getDashboard,
  });
}

export function useVariantSearch() {
  return useMutation({
    mutationFn: (query: string) => api.searchVariant(query),
  });
}

export function useVariantDetail(id: number | null) {
  return useQuery({
    queryKey: ["variant", id],
    queryFn: () => api.getVariantDetail(id!),
    enabled: id !== null,
  });
}

export function useEvidence(id: number | null) {
  return useQuery({
    queryKey: ["evidence", id],
    queryFn: () => api.getEvidence(id!),
    enabled: id !== null,
  });
}

export function useReport(id: number | null) {
  return useQuery({
    queryKey: ["report", id],
    queryFn: () => api.getReport(id!),
    enabled: id !== null,
  });
}

export function useAISummary() {
  return useMutation({
    mutationFn: (id: number) => api.generateSummary(id),
  });
}

export function useGraph(id: number | null) {
  return useQuery({
    queryKey: ["graph", id],
    queryFn: () => api.getGraph(id!),
    enabled: id !== null,
  });
}

export function useGaps(id: number | null) {
  return useQuery({
    queryKey: ["gaps", id],
    queryFn: () => api.getGaps(id!),
    enabled: id !== null,
  });
}

export function useVariants(gene?: string) {
  return useQuery({
    queryKey: ["variants", gene],
    queryFn: () => api.listVariants(gene),
  });
}

export function useCompareVariants() {
  return useMutation({
    mutationFn: ({ query1, query2 }: { query1: string; query2: string }) =>
      api.compareVariants(query1, query2),
  });
}

export function usePublicationTrends(id: number | null) {
  return useQuery({
    queryKey: ["publication-trends", id],
    queryFn: () => api.getPublicationTrends(id!),
    enabled: id !== null,
  });
}

export function useWhyMatters() {
  return useMutation({
    mutationFn: (id: number) => api.getWhyMatters(id),
  });
}
