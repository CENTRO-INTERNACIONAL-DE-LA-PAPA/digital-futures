// The shapes the API returns: the same records as src/digital_futures/state.py.

export type Source = { title: string; url: string };
export type Scope = {
  theme: string;
  geography: string;
  current_year: number;
  horizon_year: number;
  seed_drivers: string[];
  target_drivers: number;
  axis_sets: number;
};
export type Driver = { id: string; name: string; description: string; steeple: string; sources: Source[] };
export type Cluster = { name: string; rationale: string; driver_ids: string[] };
export type Score = {
  driver_id: string;
  name: string;
  impact: number;
  uncertainty: number;
  evidence: string;
  policy_attention?: number;
  policy_evidence?: string;
};
export type Critical = {
  driver_id: string;
  name: string;
  cluster: string;
  impact: number;
  uncertainty: number;
  policy_attention: number;
  rationale: string;
};
export type Axis = { driver_id: string; driver?: string; pole_a: string; pole_b: string };
export type AxisSet = { name: string; x: Axis; y: Axis; rationale?: string };
export type Signal = { axis_set: string; driver: string; pole: string; status: string; signals: string; shift?: string; sources: Source[] };
export type Evidence = { kind: string; direction: string; strength: string; what: string; source: Source };
export type Backcast = {
  axis_set: string;
  title: string;
  pathway: { year: number; what: string }[];
  signals: Evidence[];
  indicators: { name: string; meaning: string }[];
  gaps: string;
};
export type Quadrant = { axis_set: string; x_pole: string; y_pole: string; title: string; sketch: string };
export type Narrative = { axis_set?: string; title: string; personas: Record<string, string> };

export type Values = {
  scope?: Scope;
  drivers?: Driver[];
  clusters?: Cluster[];
  scores?: Score[];
  critical?: Critical[];
  axis_sets?: AxisSet[];
  signals?: Signal[];
  quadrants?: Quadrant[];
  narratives?: Narrative[];
  backcasts?: Backcast[];
};

export type Progress = { busy: boolean; working: string | null; elapsed: number; progress: { at: number; message: string }[] };
export type Run = Progress & {
  id: string;
  values: Values;
  pending: { step: string; data: any[] } | null;
  failed: { step: string; error: string } | null;
  done: string[];
};
export type RunMeta = { id: string; created: string; scope: Partial<Scope>; arm: string };

export type Totals = {
  elapsed_seconds: number | null;
  ai_seconds: number;
  review_seconds: number | null;
  ai_calls: number;
  cost: number;
  edited: number;
  revised: number;
  scenarios: number;
};
export type StepMetrics = {
  step: string;
  items: number | null;
  recorded: boolean;
  ai_runs: number;
  reused: number;
  ai_seconds: number;
  ai_calls: number;
  cost: number;
  approved: number;
  edited: number;
  revised: number;
  review_seconds: number | null;
  kept: { before: number; after: number; unchanged: number } | null;
};
export type Metrics = { arm: string; complete: boolean; steps: StepMetrics[]; totals: Totals };
export type RunRow = Totals & { id: string; created: string; arm: string; geography: string; drivers: number; clusters: number; finished: boolean };

// Every step view gets the step's records, everything else in the run, and (when the step is
// waiting for review) a way to change the records.
export type ViewProps<T> = {
  data: T[];
  values: Values;
  onChange?: (data: T[]) => void;
  sendBack?: (step: string, feedback: string) => void; // reopen an earlier step and ask the AI to revise it
};
