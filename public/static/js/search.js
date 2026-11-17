// Bilingual search with Arabic normalization.
const DIACRITICS = /[\u064B-\u065F\u0670\u06D6-\u06ED\u0640]/g; // harakat, dagger alef, tatweel

export function normalize(text) {
  return String(text ?? "")
    .normalize("NFKC")
    .toLowerCase()
    .replace(DIACRITICS, "")
    .replace(/[\u0623\u0625\u0622\u0671]/g, "\u0627") // أ إ آ ٱ -> ا
    .replace(/\u0649/g, "\u064A")                      // ى -> ي
    .replace(/\u0629/g, "\u0647")                      // ة -> ه
    .replace(/\u0624/g, "\u0648")                      // ؤ -> و
    .replace(/\u0626/g, "\u064A")                      // ئ -> ي
    .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660)) // Arabic-Indic digits
    .replace(/\s+/g, " ")
    .trim();
}

/** Precompute a searchable haystack once per partner (Arabic + English names). */
export function buildIndex(partners) {
  return partners.map((p) => ({
    id: p.id,
    haystack: normalize(`${p.name_ar ?? ""} ${p.name_en ?? ""}`),
  }));
}

export function matchesQuery(haystack, query) {
  const q = normalize(query);
  if (!q) return true;
  return q.split(" ").every((token) => haystack.includes(token));
}
