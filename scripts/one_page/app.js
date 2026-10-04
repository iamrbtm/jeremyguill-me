/* One-page site behaviour: collapsing nav and the case-study overlay.
   Dependency-free, ES2020. Without JS (or without <dialog>) every link works normally. */
(() => {
  "use strict";

  const root = document.documentElement;
  root.classList.add("js");

  /* ---- Collapsing navigation ---- */
  const toggle = document.querySelector(".nav-toggle");
  const nav = document.getElementById("site-nav");
  if (toggle && nav) {
    const setOpen = (open) => {
      nav.classList.toggle("is-open", open);
      toggle.setAttribute("aria-expanded", String(open));
    };
    toggle.addEventListener("click", () => setOpen(toggle.getAttribute("aria-expanded") !== "true"));
    nav.addEventListener("click", (event) => {
      if (event.target instanceof Element && event.target.closest("a")) setOpen(false);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && nav.classList.contains("is-open")) {
        setOpen(false);
        toggle.focus();
      }
    });
  }

  /* ---- Case-study overlay ---- */
  const dialog = document.getElementById("case-dialog");
  if (!dialog || typeof HTMLDialogElement === "undefined"
      || typeof HTMLDialogElement.prototype.showModal !== "function") {
    return;
  }
  const titleEl = document.getElementById("case-title");
  const bodyEl = document.getElementById("case-body");
  const scroller = dialog.querySelector(".case-dialog__scroll");
  const PREFIX = "#work/";
  let opener = null;
  let currentSlug = null;
  let closingFromHistory = false;

  const templateFor = (slug) => {
    for (const tpl of document.querySelectorAll("template[data-case]")) {
      if (tpl.getAttribute("data-case") === slug) return tpl;
    }
    return null;
  };
  const cardLinkFor = (slug) => {
    // Prefer the title link: the media link is aria-hidden and not focusable.
    const attr = CSS.escape(slug);
    return document.querySelector(`h3 a[data-case="${attr}"]`)
      || document.querySelector(`a[data-case="${attr}"]`);
  };
  const slugFromHash = () => {
    if (!location.hash.startsWith(PREFIX)) return null;
    try {
      return decodeURIComponent(location.hash.slice(PREFIX.length));
    } catch (error) {
      return null;
    }
  };

  const show = (slug, from) => {
    const tpl = templateFor(slug);
    if (!tpl) return false;
    titleEl.textContent = tpl.getAttribute("data-title") || "";
    bodyEl.replaceChildren(tpl.content.cloneNode(true));
    currentSlug = slug;
    opener = from || cardLinkFor(slug);
    if (!dialog.open) {
      root.classList.add("case-open");
      dialog.showModal();
    }
    scroller.scrollTop = 0;
    return true;
  };

  const openCase = (slug, from) => {
    if (!show(slug, from)) return;
    history.pushState({ case: slug }, "", PREFIX + encodeURIComponent(slug));
  };

  dialog.addEventListener("close", () => {
    root.classList.remove("case-open");
    bodyEl.replaceChildren();
    const target = opener;
    opener = null;
    currentSlug = null;
    if (!closingFromHistory && slugFromHash() !== null) {
      history.replaceState(null, "", location.pathname + location.search);
    }
    closingFromHistory = false;
    if (target && document.contains(target)) target.focus({ preventScroll: true });
  });

  dialog.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) return;
    if (target === dialog || target.closest("[data-close]")) {
      dialog.close();
      return;
    }
    // In-body anchors must never reach the router.
    const anchor = target.closest("a");
    if (anchor && (anchor.getAttribute("href") || "").startsWith("#")) event.preventDefault();
  });

  document.addEventListener("click", (event) => {
    if (event.defaultPrevented || event.button !== 0
        || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const target = event.target;
    if (!(target instanceof Element)) return;
    const link = target.closest("a[data-case]");
    if (!link) return;
    event.preventDefault();
    openCase(link.getAttribute("data-case"), link);
  });

  const syncWithHash = () => {
    const slug = slugFromHash();
    if (slug !== null) {
      if (slug !== currentSlug) show(slug, null);
    } else if (dialog.open) {
      closingFromHistory = true;
      dialog.close();
    }
  };
  window.addEventListener("popstate", syncWithHash);
  window.addEventListener("hashchange", syncWithHash);

  if (slugFromHash() !== null) show(slugFromHash(), null);
})();
