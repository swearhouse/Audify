const form = document.querySelector("#login-form");
const error = document.querySelector("#error");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  error.textContent = "";
  const formData = new FormData(form);

  try {
    const response = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: formData.get("username"),
        password: formData.get("password"),
      }),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Could not sign in.");
    }
    window.location.assign("/");
  } catch (failure) {
    error.textContent = failure.message;
  }
});
