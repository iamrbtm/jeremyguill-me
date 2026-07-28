import Editor from "@toast-ui/editor";
import "@toast-ui/editor/dist/toastui-editor.css";

type EditorMode = "markdown" | "wysiwyg";

export class PortfolioEditor {
  constructor(private readonly editor: Editor) {}

  getMarkdown(): string {
    return this.editor.getMarkdown();
  }

  setMarkdown(source: string): void {
    this.editor.setMarkdown(source, false);
  }

  toggleMode(mode: EditorMode): void {
    this.editor.changeMode(mode, true);
  }

  focus(): void {
    this.editor.focus();
  }
}

function bootEditor(container: HTMLElement): void {
  const sourceField = container.querySelector<HTMLTextAreaElement>("[data-editor-source]");
  const root = container.querySelector<HTMLElement>("[data-editor-root]");
  if (!sourceField || !root) return;

  const editor = new Editor({
    el: root,
    height: "520px",
    initialEditType: "markdown",
    initialValue: sourceField.value,
    previewStyle: "vertical",
    usageStatistics: false,
    toolbarItems: [
      ["heading", "bold", "italic"],
      ["quote", "ul", "ol"],
      ["link", "image"],
      ["code", "codeblock"],
    ],
  });
  const adapter = new PortfolioEditor(editor);
  sourceField.form?.addEventListener("submit", () => {
    sourceField.value = adapter.getMarkdown();
  });
  container.dispatchEvent(
    new CustomEvent("portfolio:editor-ready", { bubbles: true, detail: { editor: adapter } }),
  );
}

document.querySelectorAll<HTMLElement>("[data-portfolio-editor]").forEach(bootEditor);
