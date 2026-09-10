async function request(url, options = {}) {
  const response = await fetch(url, { ...options, headers: { ...(options.headers || {}) } });
  if (!response.ok) {
    throw new Error((await response.json().catch(() => ({}))).detail || "Unable to sign in");
  }
  return response;
}

async function checkSession() {
  try {
    await request("/api/auth/status");
    window.location.replace("/admin");
  } catch (_) {
    // The login form is shown when no active session exists.
  }
}

document.querySelector("#login-form").onsubmit = async (event) => {
  event.preventDefault();
  const error = document.querySelector("#login-error");
  error.textContent = "";
  try {
    await request("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: event.target.elements.password.value }),
    });
    window.location.replace("/admin");
  } catch (_) {
    error.textContent = "Unable to sign in.";
  }
};

checkSession();
