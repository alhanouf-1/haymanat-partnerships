// Category / period filtering combined with search.
import { matchesQuery } from "./search.js";

export const CATEGORIES = ["organizations", "clubs", "volunteer_teams", "initiatives", "hackathons"];
export const PERIODS = ["2025", "2026_H1", "2026_H2"];

export const state = { category: "all", period: "all", query: "" };

export function resetFilters() {
  state.category = "all";
  state.period = "all";
  state.query = "";
}

export function hasActiveFilters() {
  return state.category !== "all" || state.period !== "all" || state.query.trim() !== "";
}

export function applyFilters(partners, index) {
  const hay = new Map(index.map((i) => [i.id, i.haystack]));
  return partners.filter((p) =>
    (state.category === "all" || p.category === state.category) &&
    (state.period === "all" || p.period === state.period) &&
    matchesQuery(hay.get(p.id) ?? "", state.query));
}

/** Counts per category, honoring period + search (so chip numbers reflect the current view). */
export function categoryCounts(partners, index) {
  const hay = new Map(index.map((i) => [i.id, i.haystack]));
  const counts = { all: 0 };
  CATEGORIES.forEach((c) => (counts[c] = 0));
  partners.forEach((p) => {
    if ((state.period === "all" || p.period === state.period) && matchesQuery(hay.get(p.id) ?? "", state.query)) {
      counts.all += 1;
      counts[p.category] += 1;
    }
  });
  return counts;
}
