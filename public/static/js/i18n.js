// Local translation system: loads /api/translations/<lang>, updates DOM, lang, dir.
const STORAGE_KEY = "haymanat-lang";
const SUPPORTED = ["ar", "en"];
const DEFAULT_LANG = "ar";

const cache = {};
let current = DEFAULT_LANG;
const listeners = [];

export const getLang = () => current;
export const onLanguageChange = (fn) => listeners.push(fn);

export function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function load(lang) {
  if (!cache[lang]) {
    const res = await fetch(`/api/translations/${lang}`);
    if (!res.ok) throw new Error(`Translation load failed: ${lang}`);
    cache[lang] = await res.json();
  }
  return cache[lang];
}

export function t(key, vars = {}) {
  const dict = cache[current] || {};
  let text = dict[key];
  if (text === undefined) return key;
  for (const [k, v] of Object.entries(vars)) text = text.replaceAll(`{${k}}`, v);
  return text;
}

/** Apply translations to a root. Supports data-i18n and data-i18n-attr="attr:key;attr2:key2". */
export function applyTranslations(root = document) {
  root.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  root.querySelectorAll("[data-i18n-attr]").forEach((el) => {
    el.dataset.i18nAttr.split(";").forEach((pair) => {
      const [attr, key] = pair.split(":");
      if (attr && key) el.setAttribute(attr.trim(), t(key.trim()));
    });
  });
}

function storedLang() {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    return SUPPORTED.includes(v) ? v : DEFAULT_LANG;
  } catch { return DEFAULT_LANG; }
}

export async function setLanguage(lang, { persist = true } = {}) {
  if (!SUPPORTED.includes(lang)) lang = DEFAULT_LANG;
  await load(lang);
  current = lang;
  const html = document.documentElement;
  html.lang = lang;
  html.dir = lang === "ar" ? "rtl" : "ltr";
  if (persist) {
    try { localStorage.setItem(STORAGE_KEY, lang); } catch { /* storage unavailable */ }
  }
  document.title = t("meta.title");
  document.querySelector('meta[name="description"]')?.setAttribute("content", t("meta.description"));
  document.querySelectorAll(".lang-btn").forEach((b) =>
    b.setAttribute("aria-pressed", String(b.dataset.lang === lang)));
  applyTranslations();
  listeners.forEach((fn) => fn(lang));
}

export async function initI18n() {
  // Preload the other language in the background for instant switching.
  const lang = storedLang();
  await setLanguage(lang, { persist: false });
  document.querySelectorAll(".lang-btn").forEach((btn) =>
    btn.addEventListener("click", () => setLanguage(btn.dataset.lang)));
  SUPPORTED.filter((l) => l !== lang).forEach((l) => load(l).catch(() => {}));
}
