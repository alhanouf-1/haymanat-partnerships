// Accessible partnership detail modal: Escape, focus trap, focus restore.
import { t, getLang, applyTranslations, escapeHtml } from "./i18n.js";

const root = document.getElementById("modal");
const dialog = root.querySelector(".modal");
const body = document.getElementById("modal-body");
const closeBtn = document.getElementById("modal-close");

let currentPartner = null;
let lastTrigger = null;

export const displayName = (p) => (getLang() === "en" && p.name_en ? p.name_en : p.name_ar);

/** Only same-site paths or https URLs are allowed as logo sources. */
export function safeLogoUrl(url) {
  if (typeof url !== "string" || !url) return null;
  if (url.startsWith("/static/") && !url.includes("..")) return url;
  try { const u = new URL(url); return u.protocol === "https:" ? u.href : null; } catch { return null; }
}

function safeUrl(url) {
  try {
    const u = new URL(url);
    return ["http:", "https:"].includes(u.protocol) ? u.href : null;
  } catch { return null; }
}

function render() {
  const p = currentPartner;
  if (!p) return;
  const lang = getLang();
  const name = displayName(p);
  const desc = lang === "en" ? (p.description_en || p.description_ar) : (p.description_ar || p.description_en);
  const site = p.website ? safeUrl(p.website) : null;
  const logoUrl = safeLogoUrl(p.logo);
  const logo = logoUrl
    ? `<img src="${escapeHtml(logoUrl)}" alt="${escapeHtml(t("modal.logo_alt", { name }))}" data-hide-on-error>`
    : `<svg class="icon" aria-hidden="true"><use href="#i-${p.category}"/></svg>`;

  body.innerHTML = `
    <div class="modal-head" data-cat="${escapeHtml(p.category)}">
      <div class="modal-logo">${logo}</div>
      <h3 class="modal-title" id="modal-title" dir="auto">${escapeHtml(name)}</h3>
    </div>
    <dl class="modal-info">
      <div class="info-row"><dt>${escapeHtml(t("modal.category"))}</dt><dd>${escapeHtml(t("category." + p.category))}</dd></div>
      <div class="info-row"><dt>${escapeHtml(t("modal.period"))}</dt><dd>${escapeHtml(t("period." + p.period))}</dd></div>
      ${desc ? `<div class="info-row"><dt>${escapeHtml(t("modal.description"))}</dt><dd dir="auto">${escapeHtml(desc)}</dd></div>` : ""}
      ${site ? `<div class="info-row"><dt>${escapeHtml(t("modal.website"))}</dt><dd><a href="${escapeHtml(site)}" target="_blank" rel="noopener noreferrer">${escapeHtml(t("modal.visit_website"))}<svg class="icon" aria-hidden="true"><use href="#i-external"/></svg></a></dd></div>` : ""}
    </dl>`;
}

export function isOpen() { return !root.hidden; }

export function openModal(partner, trigger) {
  currentPartner = partner;
  lastTrigger = trigger || document.activeElement;
  render();
  root.hidden = false;
  document.body.classList.add("modal-open");
  requestAnimationFrame(() => root.classList.add("is-open"));
  closeBtn.focus();
}

export function closeModal() {
  if (root.hidden) return;
  root.classList.remove("is-open");
  const partnerId = currentPartner?.id;
  const done = () => {
    root.hidden = true;
    document.body.classList.remove("modal-open");
    currentPartner = null;
  };
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  reduce ? done() : setTimeout(done, 220);
  if (lastTrigger && document.contains(lastTrigger)) lastTrigger.focus();
  else document.querySelector(`#cards-grid .card[data-id="${partnerId}"]`)?.focus();
}

/** Re-render open modal after a language change. */
export function refreshModal() {
  if (isOpen()) { render(); applyTranslations(root); }
}

function focusables() {
  return [...dialog.querySelectorAll('a[href],button:not([disabled]),[tabindex]:not([tabindex="-1"])')]
    .filter((el) => !el.hidden && el.offsetParent !== null);
}

export function initModal() {
  closeBtn.addEventListener("click", closeModal);
  root.addEventListener("click", (e) => { if (e.target === root) closeModal(); });
  document.addEventListener("keydown", (e) => {
    if (!isOpen()) return;
    if (e.key === "Escape") { e.preventDefault(); closeModal(); return; }
    if (e.key === "Tab") {
      const items = focusables();
      if (!items.length) { e.preventDefault(); return; }
      const first = items[0], last = items[items.length - 1];
      if (e.shiftKey && (document.activeElement === first || document.activeElement === dialog)) {
        e.preventDefault(); last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault(); first.focus();
      }
    }
  });
}
