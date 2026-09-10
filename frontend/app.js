const feed = document.querySelector("#feed");
const composer = document.querySelector("#composer");
const logoutButton = document.querySelector("#logout");
const connectionStatus = document.querySelector("#connection-status");
const notificationsOpen = document.querySelector("#notifications-open");
const pageTitle = document.querySelector("#page-title");
const adminPath = window.location.pathname === "/admin" || window.location.pathname === "/admin/";

function csrfToken() {
  return document.cookie.split("; ").find((item) => item.startsWith("labboard_csrf="))?.split("=")[1] || "";
}

function renderBody(body) {
  const fragment = document.createDocumentFragment();
  const urlPattern = /https?:\/\/[^\s<]+/gi;
  let cursor = 0;
  for (const match of body.matchAll(urlPattern)) {
    const url = match[0];
    const start = match.index ?? 0;
    const trailing = url.match(/[),.!?:;]+$/)?.[0] || "";
    const linkUrl = trailing ? url.slice(0, -trailing.length) : url;
    fragment.append(document.createTextNode(body.slice(cursor, start)));
    const link = document.createElement("a");
    link.href = linkUrl;
    link.textContent = linkUrl;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    fragment.append(link, document.createTextNode(trailing));
    cursor = start + url.length;
  }
  fragment.append(document.createTextNode(body.slice(cursor)));
  return fragment;
}

async function request(url, options = {}) {
  const response = await fetch(url, { ...options, headers: { ...(options.headers || {}) } });
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || "Request failed");
  return response;
}

function render(items) {
  feed.replaceChildren();
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No announcements yet.";
    feed.append(empty);
    return;
  }
  for (const item of items) {
    const card = document.createElement("article");
    card.className = "announcement";
    const header = document.createElement("div");
    header.className = "announcement-header";
    const date = document.createElement("time");
    date.className = "date";
    date.dateTime = item.created_at;
    date.textContent = new Date(item.created_at).toLocaleString();
    header.append(date);
    if (!composer.classList.contains("hidden")) {
      const remove = document.createElement("button");
      remove.className = "button danger";
      remove.textContent = "Delete";
      remove.onclick = () => deleteAnnouncement(item.id);
      header.append(remove);
    }
    const body = document.createElement("p");
    body.className = "announcement-body";
    body.append(renderBody(item.body));
    card.append(header, body);
    if (item.attachments.length) {
      const attachments = document.createElement("div");
      attachments.className = "attachments";
      for (const attachment of item.attachments) {
        const link = document.createElement("a");
        link.className = "attachment";
        link.href = attachment.url;
        link.textContent = `${attachment.original_name} (${Math.ceil(attachment.size / 1024)} KB)`;
        attachments.append(link);
      }
      card.append(attachments);
    }
    feed.append(card);
  }
}

async function loadAnnouncements() {
  try {
    const response = await request("/api/announcements");
    render(await response.json());
  } catch (_) {
    feed.textContent = "Unable to load announcements.";
  }
}

function updateNotificationButton() {
  if (!("Notification" in window)) {
    notificationsOpen.classList.add("hidden");
  } else if (Notification.permission === "granted") {
    notificationsOpen.textContent = "Notifications on";
    notificationsOpen.disabled = true;
  } else if (Notification.permission === "denied") {
    notificationsOpen.textContent = "Notifications blocked";
    notificationsOpen.disabled = true;
  }
}

async function requestNotifications() {
  if (!("Notification" in window)) return;
  await Notification.requestPermission();
  updateNotificationButton();
}

async function handleAnnouncementEvent(event) {
  const payload = JSON.parse(event.data || "{}");
  if (payload.action !== "published") {
    await loadAnnouncements();
    return;
  }
  const response = await request("/api/announcements");
  const items = await response.json();
  const newest = items[0];
  render(items);
  if (newest && Notification.permission === "granted" && document.visibilityState !== "visible") {
    new Notification("New announcement", {
      body: newest.body.slice(0, 120),
      tag: `announcement-${newest.id}`,
    });
  }
}

async function refreshAuth() {
  if (!adminPath) {
    composer.classList.add("hidden");
    logoutButton.classList.add("hidden");
    await loadAnnouncements();
    return;
  }
  pageTitle.textContent = "Admin panel";
  try {
    await request("/api/auth/status");
    composer.classList.remove("hidden");
    logoutButton.classList.remove("hidden");
  } catch (_) {
    window.location.replace("/admin/login");
  }
  await loadAnnouncements();
}

async function deleteAnnouncement(id) {
  if (!confirm("Delete this announcement?")) return;
  await request(`/api/announcements/${id}`, { method: "DELETE", headers: { "X-CSRF-Token": csrfToken() } });
  await loadAnnouncements();
}

logoutButton.onclick = async () => {
  await request("/api/auth/logout", { method: "POST", headers: { "X-CSRF-Token": csrfToken() } });
  await refreshAuth();
};
document.querySelector("#publish-form").onsubmit = async (event) => {
  event.preventDefault();
  const error = document.querySelector("#publish-error");
  error.textContent = "";
  try {
    const form = new FormData();
    form.append("body", event.target.elements.body.value);
    for (const file of event.target.elements.files.files) {
      form.append("files", file);
    }
    await request("/api/announcements", { method: "POST", headers: { "X-CSRF-Token": csrfToken() }, body: form });
    event.target.reset();
    await loadAnnouncements();
  } catch (exception) { error.textContent = exception.message; }
};

const events = new EventSource("/events");
events.onopen = () => { connectionStatus.textContent = "Live updates on"; };
events.onerror = () => { connectionStatus.textContent = "Reconnecting…"; };
events.addEventListener("announcement", handleAnnouncementEvent);
events.addEventListener("refetch", loadAnnouncements);
notificationsOpen.onclick = requestNotifications;
updateNotificationButton();
refreshAuth();
