export class PortfolioEditor {
  constructor(sourceField, root) {
    this.sourceField = sourceField;
    this.root = root;
  }

  getMarkdown() {
    return this.sourceField.value;
  }

  setMarkdown(source) {
    this.sourceField.value = source;
  }

  toggleMode() {
    return undefined;
  }

  focus() {
    this.sourceField.focus();
  }
}

function bootEditor(container) {
  const sourceField = container.querySelector("[data-editor-source]");
  const root = container.querySelector("[data-editor-root]");
  if (!(sourceField instanceof HTMLTextAreaElement) || !(root instanceof HTMLElement)) return;

  root.hidden = true;
  const adapter = new PortfolioEditor(sourceField, root);
  sourceField.form?.addEventListener("submit", () => {
    sourceField.value = adapter.getMarkdown();
  });
  container.dispatchEvent(
    new CustomEvent("portfolio:editor-ready", { bubbles: true, detail: { editor: adapter } }),
  );
}

document.querySelectorAll("[data-portfolio-editor]").forEach(bootEditor);
