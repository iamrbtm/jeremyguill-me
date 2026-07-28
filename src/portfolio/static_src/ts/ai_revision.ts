document.querySelectorAll<HTMLElement>("[data-ai-revision]").forEach((panel) => {
  panel.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement) || !target.dataset.aiAction) return;
    panel.dispatchEvent(
      new CustomEvent("portfolio:ai-revision-request", {
        bubbles: true,
        detail: { action: target.dataset.aiAction },
      }),
    );
  });
});
