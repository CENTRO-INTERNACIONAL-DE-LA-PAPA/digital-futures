// The steps of the process, in order: what each one is, what the reviewer should check, and its view.

import type { ComponentType } from "react";
import type { Scope, Values, ViewProps } from "./types";
import { Axes, Backcasts, Clusters, CriticalDrivers, Drivers, ImpactScores, Narratives, PolicyScores, Quadrants, Signals } from "./views";

export type Step = {
  name: string; // the step's name in the graph
  key: keyof Values; // where its result lives
  n: string;
  title: string;
  what: (scope: Scope) => string;
  check: string;
  takes: string;
  View: ComponentType<ViewProps<any>>;
};

export const STEPS: Step[] = [
  {
    name: "drivers", key: "drivers", n: "2", title: "Drivers of change", takes: "about 8 minutes", View: Drivers,
    what: (s) => `The AI scanned the web and the academic literature for forces that could change ${s.theme} in ${s.geography} between ${s.current_year} and ${s.horizon_year}.`,
    check: "Is anything important missing, or framed too narrowly? Click any text to edit it, delete what does not belong, and add what the AI missed. Each driver should have a source.",
  },
  {
    name: "clusters", key: "clusters", n: "3", title: "Clusters", takes: "about 30 seconds", View: Clusters,
    what: () => "Drivers that influence each other are grouped into clusters. Later, each cluster gives one critical driver.",
    check: "A cluster should be specific, not a broad theme. Use ⇄ on a driver to move it to another cluster, and click a name to rename it.",
  },
  {
    name: "score_impact", key: "scores", n: "4a", title: "Impact and uncertainty", takes: "about 1 minute", View: ImpactScores,
    what: (s) => `Every driver gets two scores from 1 to 5: how much it could change the system by ${s.horizon_year} (impact) and how open its future is (uncertainty).`,
    check: "The AI tends to score in the middle. Click the dots to change a score where you know better.",
  },
  {
    name: "score_policy", key: "scores", n: "4b", title: "Attention in policy arenas", takes: "about 1 minute", View: PolicyScores,
    what: () => "How much attention each driver already gets in policy documents and debates, from one web search per driver. Low attention on an important driver points to a blind spot.",
    check: "Follow the links when a score surprises you. Click the dots to change a score.",
  },
  {
    name: "critical", key: "critical", n: "5", title: "Critical drivers", takes: "about 20 seconds", View: CriticalDrivers,
    what: () => "One critical driver per cluster: the one with the highest impact × uncertainty. Ties go to the driver with less policy attention.",
    check: "The rule can pick a surprising driver. Use the menu on a card to choose another driver of the same cluster.",
  },
  {
    name: "axes", key: "axis_sets", n: "6", title: "Axes of uncertainty", takes: "about 20 seconds", View: Axes,
    what: (s) => `Critical drivers are paired into scenario matrices. Each axis has two poles: two different states its driver could be in by ${s.horizon_year}.`,
    check: "Poles should be neutral (neither is 'the good one'), differ in kind rather than in degree, say one thing each, and stretch beyond today: at least one pole per axis should be a real break from what dominates now. Edit a pole, or drop a matrix with ×.",
  },
  {
    name: "signals", key: "signals", n: "6b", title: "Signals of plausibility", takes: "about 1 minute", View: Signals,
    what: () => "How far is today from each pole? The AI searched the web and the literature for signs of it: policies, lobbying, conflicts, agreements, treaties, pilots, research. It also says what would have to change for the pole to prevail.",
    check: "An axis whose two poles both exist today has low stretch: send it back for bolder poles. 'No signal found' does not mean implausible: searches cover English and well-reported places better.",
  },
  {
    name: "quadrants", key: "quadrants", n: "7", title: "Quadrants", takes: "about 15 seconds", View: Quadrants,
    what: () => "Each matrix gives four scenarios, one per combination of poles. All four are developed with the same depth.",
    check: "No scenario should be the best case or the worst case. Each needs both opportunities and hardships.",
  },
  {
    name: "narratives", key: "narratives", n: "8", title: "Narratives", takes: "about 30 seconds", View: Narratives,
    what: () => "Each scenario is told by four people who live in it: a farmer, a community leader, a scientist and a policy maker.",
    check: "These accounts are fiction to make each world concrete, not forecasts. Check that both poles show in each one.",
  },
  {
    name: "backcast", key: "backcasts", n: "9", title: "Backcasting", takes: "about 3 minutes", View: Backcasts,
    what: (s) => `Each scenario is worked backwards from ${s.horizon_year} to today. The AI then searched news, the web and the literature for evidence that the first steps are, or are not, under way.`,
    check: "This is supporting evidence for the report. Open the sources of the signals you plan to cite, and note the signals that point against a scenario. The indicators are suggestions, not checked data.",
  },
];
