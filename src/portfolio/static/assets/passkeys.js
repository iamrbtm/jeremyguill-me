function assertJson(response) {
  if (!response.ok) throw new Error("Passkey request failed");
  return response.json();
}

function assertOk(response) {
  if (!response.ok) throw new Error("Passkey ceremony failed");
}

function hexToBuffer(hex) {
  const bytes = new Uint8Array(hex.length / 2);
  for (let index = 0; index < bytes.length; index += 1) {
    bytes[index] = parseInt(hex.slice(index * 2, index * 2 + 2), 16);
  }
  return bytes.buffer;
}

async function signInWithPasskey() {
  const begin = await fetch("/admin/auth/passkey/begin", { method: "POST" }).then(assertJson);
  let assertionId = "";

  if (window.PublicKeyCredential && navigator.credentials) {
    const assertion = await navigator.credentials.get({
      publicKey: {
        challenge: hexToBuffer(begin.options.challenge),
        rpId: begin.options.rpId,
        userVerification: begin.options.userVerification || "required",
        timeout: 60000,
      },
    });
    assertionId = assertion?.id || "";
  }

  await fetch("/admin/auth/passkey/finish", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      challenge_id: begin.challenge_id,
      credential: {
        id: assertionId,
        origin: window.location.origin,
        rp_id: begin.options.rpId,
        user_verified: true,
      },
    }),
  }).then(assertOk);
  window.location.assign("/admin");
}

document.querySelector("[data-passkey-sign-in]")?.addEventListener("click", () => {
  void signInWithPasskey();
});
