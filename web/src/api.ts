import type { KnowledgeObject } from "./types";

export async function fetchKnowledge(): Promise<KnowledgeObject[]> {
  const response = await fetch("/api/knowledge");
  if (!response.ok) {
    throw new Error(`Failed to fetch knowledge: ${response.status}`);
  }
  return response.json();
}
