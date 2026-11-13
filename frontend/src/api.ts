import type { Progress, Run, RunMeta, Scope } from "./types";

async function call<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, body === undefined ? undefined : {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().then((j) => j.detail, () => null);
    throw new Error(typeof detail === "string" ? detail : `${res.status} ${res.statusText}`);
  }
  return res.json();
}

export const api = {
  meta: () => call<{ default_scope: Scope }>("/meta"),
  runs: () => call<RunMeta[]>("/runs"),
  run: (id: string) => call<Run>(`/runs/${id}`),
  progress: (id: string) => call<Progress>(`/runs/${id}/progress`),
  create: (scope: Scope, hitl: boolean) => call<{ id: string }>("/runs", { scope, hitl }),
  review: (id: string, decision: object) => call(`/runs/${id}/review`, decision),
  retry: (id: string) => call(`/runs/${id}/retry`, {}),
  reopen: (id: string, step: string) => call(`/runs/${id}/reopen`, { step }),
  activity: () => call<{ lines: string[]; spent: number }>("/activity"),
};
