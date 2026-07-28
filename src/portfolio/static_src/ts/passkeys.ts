import { startAuthentication } from "@simplewebauthn/browser";

function assertJson(response: Response): Promise<any> {
  if (!response.ok) throw new Error("Passkey request failed");
  return response.json();
}

function assertOk(response: Response): void {
  if (!response.ok) throw new Error("Passkey ceremony failed");
}

export async function signInWithPasskey(): Promise<void> {
  const begin = await fetch("/admin/auth/passkey/begin", { method: "POST" }).then(assertJson);
  const credential = await startAuthentication({ optionsJSON: begin.options });
  await fetch("/admin/auth/passkey/finish", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ challenge_id: begin.challenge_id, credential }),
  }).then(assertOk);
  window.location.assign("/admin");
}

document.querySelector("[data-passkey-sign-in]")?.addEventListener("click", () => {
  void signInWithPasskey();
});
