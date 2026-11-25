// App entry: loads data, wires i18n, search, filters, modal, stats, nav.
import { initI18n, onLanguageChange, t, getLang, applyTranslations, escapeHtml } from "./i18n.js";
import { buildIndex } from "./search.js";
import { CATEGORIES, PERIODS, state, applyFilters, categoryCounts, resetFilters } from "./filters.js";
import { initModal, openModal, refreshModal, displayName, safeLogoUrl } from "./modals.js";

const $ = (id) => document.getElementById(id);
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

let partners = [];
let index = [];
let statsBuilt = false;

/* ---------- Stats (computed from data) ---------- */
function buildStats() {
  const counts = { total: partners.length };
  CATEGORIES.forEach((c) => (counts[c] = partners.filter((p) => p.category === c).length));
  $("stats-grid").innerHTML = ["total", ...CATEGORIES].map((key) => `
    <div class="stat-card ${key === "total" ? "stat-card--total" : ""} reveal" data-cat="${key}">
      <span class="stat-icon"><svg class="icon" aria-hidden="true"><use href="#i-${key}"/></svg></span>
      <span class="stat-num" data-target="${counts[key]}">${reduceMotion ? counts[key] : 0}</span>
      <span class="stat-label" data-i18n="stats.${key}"></span>
    </div>`).join("");
  applyTranslations($("stats-grid"));
  statsBuilt = true;

  const grid = $("stats-grid");
  const run = () => grid.querySelectorAll(".stat-num").forEach(animateCount);
  grid.querySelectorAll(".reveal").forEach((el) => observeReveal(el));
  if (reduceMotion || !("IntersectionObserver" in window)) { run(); return; }
  const io = new IntersectionObserver((entries) => {
    if (entries.some((e) => e.isIntersecting)) { run(); io.disconnect(); }
  }, { threshold: 0.3 });
  io.observe(grid);
}

function animateCount(el) {
  const target = Number(el.dataset.target);
  if (reduceMotion) { el.textContent = target; return; }
  const dur = 900, start = performance.now();
  const step = (now) => {
    const p = Math.min((now - start) / dur, 1);
    el.textContent = Math.round(target * (1 - Math.pow(1 - p, 3)));
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

/* ---------- Filters UI ---------- */
function renderChips() {
  const counts = categoryCounts(partners, index);
  const keys = ["all", ...CATEGORIES];
  $("category-chips").innerHTML = keys.map((k) => `
    <button type="button" class="chip" data-category="${k}" aria-pressed="${state.category === k}"
      ${k === "all" ? "" : `data-cat="${k}"`}>
      <span class="dot" aria-hidden="true"></span>
      <span>${escapeHtml(t("category." + k))}</span>
      <span class="n">${counts[k]}</span>
    </button>`).join("");
}

function renderPeriodOptions() {
  const sel = $("period-select");
  sel.innerHTML = ["all", ...PERIODS].map((p) =>
    `<option value="${p}">${escapeHtml(t("period." + p))}</option>`).join("");
  sel.value = state.period;
}

/* ---------- Cards ---------- */
function cardHtml(p, i) {
  const name = displayName(p);
  const logo = safeLogoUrl(p.logo);
  const avatar = logo
    ? `<img src="${escapeHtml(logo)}" alt="" loading="lazy" data-hide-on-error>`
    : `<svg class="icon" aria-hidden="true"><use href="#i-${p.category}"/></svg>`;
  return `
    <button type="button" class="card" data-id="${escapeHtml(p.id)}" data-category="${p.category}"
      aria-label="${escapeHtml(t("card.open_label", { name }))}">
      <span class="card-top">
        <span class="avatar">${avatar}</span>
        <span class="badge">${escapeHtml(t("category." + p.category))}</span>
      </span>
      <span class="card-name" dir="auto">${escapeHtml(name)}</span>
      <span class="card-meta">
        <span>${escapeHtml(t("period." + p.period))}</span>
        <span class="card-more">${escapeHtml(t("card.view_details"))}<svg class="icon icon-dir" aria-hidden="true"><use href="#i-arrow"/></svg></span>
      </span>
    </button>`;
}

function renderResults() {
  const list = applyFilters(partners, index);
  $("cards-grid").innerHTML = list.map(cardHtml).join("");
  $("cards-grid").querySelectorAll(".card").forEach((el, i) => { el.style.animationDelay = `${Math.min(i, 12) * 25}ms`; });
  $("empty-state").hidden = list.length > 0;
  $("results-count").textContent = t("results.count_of", { count: list.length, total: partners.length });
  $("search-clear").hidden = state.query === "";
}

function update({ chips = true } = {}) {
  if (chips) renderChips();
  renderResults();
}

function syncControls() {
  $("search-input").value = state.query;
  $("period-select").value = state.period;
}

/* ---------- Header / nav / reveal ---------- */
let revealIO;
function observeReveal(el) {
  if (!("IntersectionObserver" in window) || reduceMotion) { el.classList.add("is-visible"); return; }
  revealIO ??= new IntersectionObserver((entries) => entries.forEach((e) => {
    if (e.isIntersecting) { e.target.classList.add("is-visible"); revealIO.unobserve(e.target); }
  }), { threshold: 0.12 });
  revealIO.observe(el);
}

function initNav() {
  const toggle = $("menu-toggle"), nav = $("main-nav");
  const setOpen = (open) => { nav.classList.toggle("is-open", open); toggle.setAttribute("aria-expanded", String(open)); };
  toggle.addEventListener("click", () => setOpen(!nav.classList.contains("is-open")));
  nav.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => setOpen(false)));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") setOpen(false); });

  const links = [...nav.querySelectorAll(".nav-link")];
  const sections = ["partners", "about"].map((id) => $(id)).filter(Boolean);
  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (!e.isIntersecting) return;
      links.forEach((l) => l.classList.toggle("is-active", l.getAttribute("href") === `#${e.target.id}`));
    }), { rootMargin: "-40% 0px -55% 0px" });
    sections.forEach((s) => io.observe(s));
  }
}

function initControls() {
  // Broken images: hide them (CSP forbids inline onerror handlers). `error` does not bubble, so capture.
  document.addEventListener("error", (e) => {
    const el = e.target;
    if (!(el instanceof HTMLImageElement)) return;
    if (el.hasAttribute("data-hide-on-error")) { el.remove(); return; }
    const cat = el.dataset.fallbackIcon;   // modal logo failed to load: show the default category icon
    if (cat && CATEGORIES.includes(cat)) {
      const ns = "http://www.w3.org/2000/svg";
      const svg = document.createElementNS(ns, "svg");
      svg.setAttribute("class", "icon");
      svg.setAttribute("aria-hidden", "true");
      const use = document.createElementNS(ns, "use");
      use.setAttribute("href", `#i-${cat}`);
      svg.appendChild(use);
      el.replaceWith(svg);
    }
  }, true);
  $("search-input").addEventListener("input", (e) => { state.query = e.target.value; update(); });
  $("search-clear").addEventListener("click", () => { state.query = ""; syncControls(); update(); $("search-input").focus(); });
  $("period-select").addEventListener("change", (e) => { state.period = e.target.value; update(); });
  $("category-chips").addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    state.category = chip.dataset.category;
    update();
    $("category-chips").querySelector(`[data-category="${state.category}"]`)?.focus();
  });
  $("empty-reset").addEventListener("click", () => { resetFilters(); syncControls(); update(); });
  $("cards-grid").addEventListener("click", (e) => {
    const card = e.target.closest(".card");
    if (!card) return;
    const p = partners.find((x) => x.id === card.dataset.id);
    if (p) openModal(p, card);
  });
}

/* ---------- Boot ---------- */
async function loadPartners() {
  const res = await fetch("/api/partners");
  if (!res.ok) throw new Error("partners load failed");
  const data = await res.json();
  if (!Array.isArray(data)) throw new Error("invalid partners data");
  // Defensive validation: only well-formed records with known category/period are rendered.
  return data.filter((p) => p && typeof p.id === "string" && /^[\w-]+$/.test(p.id) &&
    typeof p.name_ar === "string" && p.name_ar.trim() &&
    CATEGORIES.includes(p.category) && PERIODS.includes(p.period));
}

async function main() {
  $("year").textContent = new Date().getFullYear();
  document.querySelectorAll(".hero .reveal").forEach(observeReveal);
  initNav();
  initModal();
  await initI18n();
  document.documentElement.classList.remove("i18n-pending");

  try {
    partners = await loadPartners();
  } catch (err) {
    console.error(err);
    $("error-state").hidden = false;
    $("results-count").textContent = "";
    return;
  }
  index = buildIndex(partners);
  buildStats();
  renderPeriodOptions();
  initControls();
  update();

  onLanguageChange(() => {
    renderPeriodOptions();            // filters/search state is preserved (kept in `state`)
    update();
    refreshModal();
    applyTranslations($("stats-grid"));
  });
}

main().catch((e) => { console.error(e); document.documentElement.classList.remove("i18n-pending"); });
