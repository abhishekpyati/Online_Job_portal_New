const API_BASE = window.API_BASE || "http://127.0.0.1:8000/api";
const WS_BASE = API_BASE.replace(/^http/, "ws");

const state = {
  token: localStorage.getItem("token"),
  user: null,
  websocket: null,
  editJobId: null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function showAlert(message, type = "success") {
  const detail = Array.isArray(message) ? message.map((item) => item.msg || JSON.stringify(item)).join("<br>") : message;
  $("#globalAlert").innerHTML = `<div class="alert alert-${type} alert-dismissible fade show shadow-sm">${detail}<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>`;
  setTimeout(() => ($("#globalAlert").innerHTML = ""), 4500);
}

async function api(path, options = {}) {
  if (window.location.protocol === "file:") {
    throw new Error("Frontend must be served over HTTP. Run `npm run dev` and open the app at http://127.0.0.1:5173 instead of opening index.html directly.");
  }
  const headers = options.headers || {};
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  try {
    const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Request failed" }));
      if (Array.isArray(error.detail)) {
        throw new Error(error.detail.map((item) => item.msg || JSON.stringify(item)).join("; "));
      }
      throw new Error(error.detail || "Request failed");
    }
    if (response.status === 204) return null;
    return response.json();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`API ${path} failed: ${message}`);
  }
}

async function downloadResume(applicationId) {
  const response = await fetch(`${API_BASE}/applications/${applicationId}/resume`, {
    headers: { Authorization: `Bearer ${state.token}` },
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Resume download failed" }));
    throw new Error(error.detail || "Resume download failed");
  }
  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") || "";
  const filenameMatch = disposition.match(/filename="?([^"]+)"?/i);
  const filename = filenameMatch?.[1] || `resume-${applicationId}`;
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function formJSON(form) {
  const data = Object.fromEntries(new FormData(form).entries());
  Object.keys(data).forEach((key) => {
    if (typeof data[key] === "string") data[key] = data[key].trim();
  });
  for (const key of ["salary_min", "salary_max"]) {
    if (key in data) data[key] = data[key] ? Number(data[key]) : null;
  }
  if ("skills" in data) data.skills = data.skills.split(",").map((item) => item.trim()).filter(Boolean);
  return data;
}

function jobFormJSON(form) {
  const data = formJSON(form);
  data.company_id = null;
  if (!data.salary_min) data.salary_min = null;
  if (!data.salary_max) data.salary_max = null;
  return data;
}

function setView(name) {
  state.currentView = name;
  $$(".view-section").forEach((section) => section.classList.add("d-none"));
  $(`#${name}View`).classList.remove("d-none");
  $$(".sidebar .nav-link").forEach((button) => button.classList.toggle("active", button.dataset.view === name));
  refreshCurrentView(name);
}

function roleClass(role) {
  return role === "applicant" ? "applicant-only" : role === "recruiter" ? "recruiter-only" : "admin-only";
}

async function loadSession() {
  if (!state.token) return showAuth();
  try {
    state.user = await api("/users/me");
    showApp();
    connectNotifications();
    await refreshAll();
  } catch {
    logout();
  }
}

function resetJobForm() {
  const form = $("#jobForm");
  form.reset();
  state.editJobId = null;
  $("#jobFormTitle").textContent = "Create Job";
  $("#jobSubmitButton").textContent = "Post Job";
  $("#cancelJobEdit").classList.add("d-none");
}

function populateJobForm(job) {
  const form = $("#jobForm");
  state.editJobId = job.id;
  form.elements.title.value = job.title || "";
  form.elements.location.value = job.location || "";
  form.elements.salary_min.value = job.salary_min ?? "";
  form.elements.salary_max.value = job.salary_max ?? "";
  form.elements.job_type.value = job.job_type || "full_time";
  form.elements.experience_level.value = job.experience_level || "entry";
  form.elements.skills.value = (job.skills || []).map((skill) => skill.name).join(", ");
  form.elements.description.value = job.description || "";
  $("#jobFormTitle").textContent = "Edit Job";
  $("#jobSubmitButton").textContent = "Save Changes";
  $("#cancelJobEdit").classList.remove("d-none");
}

function showAuth() {
  $("#authView").classList.remove("d-none");
  $("#appView").classList.add("d-none");
  $("#logoutBtn").classList.add("d-none");
  $("#currentUser").textContent = "";
}

function showApp() {
  $("#authView").classList.add("d-none");
  $("#appView").classList.remove("d-none");
  $("#logoutBtn").classList.remove("d-none");
  $("#currentUser").textContent = `${state.user.full_name} · ${state.user.role}`;
  $$(".applicant-only,.recruiter-only,.admin-only").forEach((el) => el.classList.add("d-none"));
  $$(`.${roleClass(state.user.role)}`).forEach((el) => el.classList.remove("d-none"));
}

function logout() {
  localStorage.removeItem("token");
  state.token = null;
  state.user = null;
  if (state.websocket) state.websocket.close();
  showAuth();
}

function stat(label, value) {
  return `<div class="surface stat"><span class="text-muted">${label}</span><strong>${value}</strong></div>`;
}

function jobItem(job, mode = "browse") {
  const skills = (job.skills || []).map((skill) => `<span class="pill">${skill.name}</span>`).join("") || `<span class="text-muted">Not specified</span>`;
  const salary = job.salary_min || job.salary_max ? `${job.salary_min || ""} - ${job.salary_max || ""}` : "Salary not listed";
  const actions = {
    browse: `<button type="button" class="btn btn-primary btn-sm" data-apply="${job.id}">Apply</button><button type="button" class="btn btn-outline-secondary btn-sm" data-save="${job.id}">Save</button>`,
    recruiter: `<button type="button" class="btn btn-outline-primary btn-sm" data-candidates="${job.id}">Top Candidates</button><button type="button" class="btn btn-outline-secondary btn-sm" data-edit-job="${job.id}">Edit</button><button type="button" class="btn btn-outline-danger btn-sm" data-delete-job="${job.id}">Delete</button>`,
    admin: `<button type="button" class="btn btn-outline-danger btn-sm" data-admin-delete-job="${job.id}">Delete</button>`,
  }[mode] || "";
  return `<article class="item">
    <div class="item-title"><div><h3>${job.title}</h3><p class="text-muted mb-0">Company: ${job.company?.name || "Company"}</p></div><div class="d-flex gap-2">${actions}</div></div>
    <p class="job-description">${job.description}</p>
    <div class="job-details">
      <div><span>Salary</span><strong>${salary}</strong></div>
      <div><span>Location</span><strong>${job.location}</strong></div>
      <div><span>Job Level</span><strong>${job.experience_level}</strong></div>
      <div><span>Job Type</span><strong>${job.job_type}</strong></div>
    </div>
    <div class="required-skills"><span>Required Skills</span><div class="pill-row">${skills}</div></div>
  </article>`;
}

function applicationItem(application, recruiter = false) {
  const status = application.status;
  const profile = application.applicant_profile;
  const skillPills = (profile?.skills || []).map((skill) => `<span class="pill">${skill.name}</span>`).join("") || `<span class="text-muted">No skills added</span>`;
  const controls = recruiter
    ? `<select class="form-select form-select-sm w-auto" data-status="${application.id}" data-current-status="${status}">
        ${["applied", "shortlisted", "rejected", "interview_scheduled"].map((value) => {
          const disabled = (status === "shortlisted" && value === "rejected") || (status === "rejected" && value === "shortlisted");
          return `<option value="${value}" ${value === status ? "selected" : ""} ${disabled ? "disabled" : ""}>${value}</option>`;
        }).join("")}
      </select>`
    : "";
  const canDownloadResume = !!profile?.resume_path;
  const canCheckSuitability = recruiter && !!application.applicant;
  const recruiterDetails = recruiter
    ? `<div class="job-details">
        <div><span>Applicant</span><strong>${application.applicant?.full_name || "Applicant"}</strong></div>
        <div><span>Email</span><strong>${application.applicant?.email || "Not available"}</strong></div>
        <div><span>Location</span><strong>${profile?.location || "Not added"}</strong></div>
      </div>
      <div class="required-skills"><span>Applicant Skills</span><div class="pill-row">${skillPills}</div></div>
      <div class="application-notes">
        <p><span>Education</span>${profile?.education || "Not added"}</p>
        <p><span>Experience</span>${profile?.experience || "Not added"}</p>
        <p><span>Cover Letter</span>${application.cover_letter || "No cover letter submitted."}</p>
      </div>
      <div class="application-actions">
        <button class="btn btn-outline-primary btn-sm" data-suitability="${application.id}" ${canCheckSuitability ? "" : "disabled title=\"No applicant information available\""}>Suitability Check</button>
        <button class="btn btn-outline-primary btn-sm" data-resume="${application.id}" ${canDownloadResume ? "" : "disabled title=\"No resume uploaded\""}>Download Resume</button>
      </div>
      <div id="suitability-${application.id}" class="suitability-box d-none"></div>`
    : ``;
  return `<article class="item">
    <div class="item-title">
      <div><h3>${application.job?.title || "Job"}</h3><p class="text-muted mb-0">${recruiter ? application.applicant?.full_name : application.job?.location || ""}</p></div>
      <div class="d-flex gap-2 align-items-center"><span class="fw-bold status-${status}">${status}</span>${controls}</div>
    </div>
    ${recruiterDetails}
  </article>`;
}

function suitabilityResult(item) {
  const matched = item.matched_skills.map((skill) => `<span class="pill">${skill}</span>`).join("") || `<span class="text-muted">No required skills matched</span>`;
  const missing = item.missing_skills.map((skill) => `<span class="pill pill-danger">${skill}</span>`).join("") || `<span class="text-muted">No missing required skills</span>`;
  return `<div class="job-details">
      <div><span>Suitability Score</span><strong>${item.score_out_of_10}/10</strong></div>
      <div><span>Recommendation</span><strong>${item.recommendation}</strong></div>
      <div><span>Checked By</span><strong>${item.source === "openai" ? "AI" : "Local Matcher"}</strong></div>
    </div>
    <div class="application-notes"><p><span>Summary</span>${item.summary || "No summary available."}</p></div>
    <div class="required-skills"><span>Matched Skills</span><div class="pill-row">${matched}</div></div>
    <div class="required-skills"><span>Missing Skills</span><div class="pill-row">${missing}</div></div>`;
}

function notificationItem(notification) {
  return `<article class="item"><div class="item-title"><p class="mb-0">${notification.message}</p><span class="small text-muted">${new Date(notification.created_at).toLocaleString()}</span></div></article>`;
}

async function refreshDashboard() {
  $("#dashboardTitle").textContent = `${state.user.role[0].toUpperCase()}${state.user.role.slice(1)} Overview`;
  const notifications = await api("/notifications");
  $("#dashboardNotifications").innerHTML = notifications.slice(0, 6).map(notificationItem).join("") || `<p class="text-muted">No notifications yet.</p>`;

  if (state.user.role === "applicant") {
    const [applications, recommended, profile] = await Promise.all([api("/applications/me"), api("/matching/recommended-jobs"), api("/profiles/applicant/me")]);
    $("#statsGrid").innerHTML = stat("Applications", applications.length) + stat("Recommended", recommended.length) + stat("Profile", `${profile.completion_percentage}%`);
    $("#primaryListTitle").textContent = "Recommended Jobs";
    // Apply client-side company filter if present
    const companyFilterEl = $("#dashboardCompanyFilter");
    const companyFilter = companyFilterEl ? companyFilterEl.value.trim().toLowerCase() : "";
    let displayed = recommended;
    if (companyFilter) {
      displayed = recommended.filter((item) => (item.job.company?.name || "").toLowerCase().includes(companyFilter));
    }
    $("#primaryList").innerHTML = displayed.map((item) => jobItem(item.job, "browse")).join("") || `<p class="text-muted">Complete your profile to improve recommendations.</p>`;
  } else if (state.user.role === "recruiter") {
    const [jobs, applications] = await Promise.all([api("/jobs/mine"), api("/applications/recruiter")]);
    $("#statsGrid").innerHTML = stat("Jobs Posted", jobs.length) + stat("Applicants", applications.length);
    $("#primaryListTitle").textContent = "Recent Applicants";
    $("#primaryList").innerHTML = applications.slice(0, 6).map((item) => applicationItem(item, true)).join("") || `<p class="text-muted">No applicants yet.</p>`;
  } else {
    const analytics = await api("/admin/analytics");
    $("#statsGrid").innerHTML = Object.entries(analytics).map(([key, value]) => stat(key, value)).join("");
    $("#primaryListTitle").textContent = "Admin";
    $("#primaryList").innerHTML = `<p class="text-muted">Use the Admin tab to manage users and jobs.</p>`;
  }
}

async function refreshJobs() {
  const query = new URLSearchParams(new FormData($("#jobSearchForm")));
  [...query.entries()].forEach(([key, value]) => !value && query.delete(key));
  const jobs = state.user.role === "recruiter" ? await api("/jobs/mine") : await api(`/jobs?${query.toString()}`);
  const mode = state.user.role === "recruiter" ? "recruiter" : state.user.role === "admin" ? "admin" : "browse";
  $("#jobsList").innerHTML = jobs.map((job) => jobItem(job, mode)).join("") || `<p class="text-muted">No jobs found.</p>`;
}

async function refreshApplications() {
  if (state.user.role === "admin") {
    $("#applicationsList").innerHTML = `<p class="text-muted">Admins monitor applications through analytics.</p>`;
    return;
  }
  const applications = await api(state.user.role === "recruiter" ? "/applications/recruiter" : "/applications/me");
  $("#applicationsList").innerHTML = applications.map((item) => applicationItem(item, state.user.role === "recruiter")).join("") || `<p class="text-muted">No applications yet.</p>`;
}

async function refreshProfile() {
  if (state.user.role === "applicant") {
    const profile = await api("/profiles/applicant/me");
    const form = $("#applicantProfileForm");
    ["phone", "location", "headline", "summary", "education", "experience"].forEach((key) => (form.elements[key].value = profile[key] || ""));
    form.elements.skills.value = profile.skills.map((skill) => skill.name).join(", ");
    $("#completionBadge").textContent = `${profile.completion_percentage}% complete`;
  } else if (state.user.role === "recruiter") {
    const companies = await api("/profiles/company/me");
    const company = companies[0];
    const form = $("#companyForm");
    ["company_id", "name", "website", "location", "description"].forEach((key) => {
      form.elements[key].value = company?.[key === "company_id" ? "id" : key] || "";
    });
  }
}

async function refreshNotifications() {
  const notifications = await api("/notifications");
  $("#notificationsList").innerHTML = notifications.map(notificationItem).join("") || `<p class="text-muted">No notifications yet.</p>`;
}

async function refreshAdmin() {
  if (state.user.role !== "admin") return;
  const [analytics, users, jobs] = await Promise.all([api("/admin/analytics"), api("/admin/users"), api("/admin/jobs")]);
  $("#adminStats").innerHTML = Object.entries(analytics).map(([key, value]) => stat(key, value)).join("");
  $("#adminUsers").innerHTML = users.map((user) => `<article class="item"><h3>${user.full_name}</h3><p class="mb-0 text-muted">${user.email} · ${user.role} · ${user.is_active ? "active" : "inactive"}</p></article>`).join("");
  $("#adminJobs").innerHTML = jobs.map((job) => jobItem(job, "admin")).join("");
}

function refreshCurrentView(name) {
  const loaders = { dashboard: refreshDashboard, jobs: refreshJobs, applications: refreshApplications, profile: refreshProfile, notifications: refreshNotifications, admin: refreshAdmin };
  return loaders[name]?.().catch((error) => showAlert(error.message, "danger"));
}

async function refreshAll() {
  await refreshDashboard();
}

function connectNotifications() {
  if (!state.token) return;
  state.websocket = new WebSocket(`${WS_BASE}/notifications/ws?token=${state.token}`);
  state.websocket.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type === "job_deleted") {
      if (state.user?.role === "applicant") {
        refreshCurrentView(state.currentView || "jobs");
      }
      return;
    }
    showAlert(payload.message, "info");
    refreshDashboard();
    refreshNotifications();
  };
}

$("#loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const token = await api("/auth/login", { method: "POST", body: JSON.stringify(formJSON(event.target)) });
    state.token = token.access_token;
    localStorage.setItem("token", state.token);
    await loadSession();
  } catch (error) {
    showAlert(error.message, "danger");
  }
});

$("#registerForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const payload = formJSON(event.target);
    await api("/auth/register", { method: "POST", body: JSON.stringify(payload) });
    const token = await api("/auth/login", { method: "POST", body: JSON.stringify({ email: payload.email, password: payload.password }) });
    state.token = token.access_token;
    localStorage.setItem("token", state.token);
    event.target.reset();
    showAlert("Account created successfully.");
    await loadSession();
  } catch (error) {
    showAlert(error.message, "danger");
  }
});

$("#logoutBtn").addEventListener("click", logout);

$("#showRegisterBtn").addEventListener("click", () => {
  $("#loginForm").classList.add("d-none");
  $("#registerForm").classList.remove("d-none");
});

$("#showLoginBtn").addEventListener("click", () => {
  $("#registerForm").classList.add("d-none");
  $("#loginForm").classList.remove("d-none");
});

$$(".sidebar .nav-link,[data-view-jump]").forEach((button) => {
  button.addEventListener("click", () => setView(button.dataset.view || button.dataset.viewJump));
});

$("#jobSearchForm").addEventListener("submit", (event) => {
  event.preventDefault();
  refreshJobs();
});

$("#jobForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    if (state.editJobId) {
      await api(`/jobs/${state.editJobId}`, { method: "PUT", body: JSON.stringify(jobFormJSON(event.target)) });
      showAlert("Job updated.");
    } else {
      await api("/jobs", { method: "POST", body: JSON.stringify(jobFormJSON(event.target)) });
      showAlert("Job posted.");
    }
    resetJobForm();
    refreshJobs();
  } catch (error) {
    showAlert(error.message, "danger");
  }
});

$("#cancelJobEdit").addEventListener("click", () => {
  resetJobForm();
});

async function handleJobButton(event) {
  event.preventDefault();
  const button = event.target.closest("button");
  if (!button) return;
  const isJobAction = button.dataset.apply || button.dataset.save || button.dataset.deleteJob || button.dataset.adminDeleteJob || button.dataset.candidates || button.dataset.editJob;
  if (!isJobAction) return;
  try {
    if (button.dataset.apply) {
      await api("/applications", { method: "POST", body: JSON.stringify({ job_id: Number(button.dataset.apply) }) });
      showAlert("Application submitted.");
      refreshDashboard();
      refreshApplications();
      return;
    }
    if (button.dataset.save) {
      await api(`/jobs/${button.dataset.save}/save`, { method: "POST" });
      showAlert("Job saved.");
      return;
    }
    if (button.dataset.deleteJob) {
      await api(`/jobs/${button.dataset.deleteJob}`, { method: "DELETE" });
      showAlert("Job deleted.");
      refreshJobs();
      return;
    }
    if (button.dataset.adminDeleteJob) {
      await api(`/admin/jobs/${button.dataset.adminDeleteJob}`, { method: "DELETE" });
      showAlert("Job deleted.");
      refreshJobs();
      return;
    }
    if (button.dataset.candidates) {
      const candidates = await api(`/matching/jobs/${button.dataset.candidates}/candidates`);
      $("#jobsList").insertAdjacentHTML("afterbegin", `<div class="surface"><h2>Top Candidates</h2>${candidates.map((item) => applicationItem(item.application, true)).join("") || "<p class='text-muted'>No candidates yet.</p>"}</div>`);
      return;
    }
    if (button.dataset.editJob) {
      const job = await api(`/jobs/${button.dataset.editJob}`);
      populateJobForm(job);
      setView("jobs");
      return;
    }
    showAlert("Action completed.");
    refreshJobs();
  } catch (error) {
    showAlert(error.message, "danger");
  }
}

$("#jobsList").addEventListener("click", handleJobButton);
$("#primaryList").addEventListener("click", handleJobButton);

// Dashboard company filter actions (applicant-only)
document.addEventListener("click", (e) => {
  const btn = e.target.closest && e.target.closest("#dashboardCompanySearch, #dashboardCompanyClear");
  if (!btn) return;
  if (btn.id === "dashboardCompanySearch") {
    refreshDashboard();
  } else if (btn.id === "dashboardCompanyClear") {
    const el = $("#dashboardCompanyFilter");
    if (el) el.value = "";
    refreshDashboard();
  }
});

$("#adminJobs").addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button?.dataset.adminDeleteJob) return;
  try {
    await api(`/admin/jobs/${button.dataset.adminDeleteJob}`, { method: "DELETE" });
    showAlert("Job deleted.");
    refreshAdmin();
  } catch (error) {
    showAlert(error.message, "danger");
  }
});

function handleStatusChange(event) {
  if (!event.target.dataset.status) return;
  const appId = event.target.dataset.status;
  const currentStatus = event.target.dataset.currentStatus;
  const newStatus = event.target.value;
  if ((currentStatus === "shortlisted" && newStatus === "rejected") || (currentStatus === "rejected" && newStatus === "shortlisted")) {
    showAlert("You cannot change a shortlisted applicant to not shortlisted (or vice versa) for the same job.", "warning");
    event.target.value = currentStatus;
    return;
  }
  api(`/applications/${appId}/status`, { method: "PUT", body: JSON.stringify({ status: newStatus }) })
    .then(() => {
      showAlert("Application status updated.");
      event.target.dataset.currentStatus = newStatus;
      refreshApplications();
      if (state.user?.role === "recruiter") {
        refreshDashboard();
      }
    })
    .catch((error) => {
      showAlert(error.message, "danger");
      event.target.value = currentStatus;
    });
}

$("#applicationsList").addEventListener("change", handleStatusChange);
$("#primaryList").addEventListener("change", handleStatusChange);

async function handleApplicationButton(event) {
  const button = event.target.closest("button");
  if (!button) return;
  try {
    if (button.dataset.resume) {
      await downloadResume(button.dataset.resume);
      return;
    }
    if (button.dataset.suitability) {
      event.preventDefault();
      const id = button.dataset.suitability;
      const originalText = button.textContent;
      try {
        button.disabled = true;
        button.textContent = "Checking...";
        const result = await api(`/applications/${id}/suitability`);
        const item = button.closest("article");
        const target = item?.querySelector(`#suitability-${id}`) || $(`#suitability-${id}`);
        if (!target) throw new Error("Suitability container not found");
        target.innerHTML = suitabilityResult(result);
        target.classList.remove("d-none");
      } finally {
        button.disabled = false;
        button.textContent = originalText;
      }
      return;
    }
    if (button.dataset.statusAction) {
      await api(`/applications/${button.dataset.statusAction}/status`, { method: "PUT", body: JSON.stringify({ status: button.dataset.nextStatus }) });
      showAlert(button.dataset.nextStatus === "shortlisted" ? "Applicant shortlisted and notified." : "Applicant marked not shortlisted and notified.");
      refreshApplications();
      refreshDashboard();
    }
  } catch (error) {
    showAlert(error.message, "danger");
  }
}

$("#applicationsList").addEventListener("click", handleApplicationButton);
$("#primaryList").addEventListener("click", handleApplicationButton);

$("#applicantProfileForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/profiles/applicant/me", { method: "PUT", body: JSON.stringify(formJSON(event.target)) });
    showAlert("Profile saved.");
    refreshProfile();
  } catch (error) {
    showAlert(error.message, "danger");
  }
});

$("#companyForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const payload = formJSON(event.target);
    const companyId = payload.company_id;
    delete payload.company_id;
    const method = companyId ? "PUT" : "POST";
    await api("/profiles/company/me", { method, body: JSON.stringify(payload) });
    showAlert("Company saved.");
    refreshProfile();
  } catch (error) {
    showAlert(error.message, "danger");
  }
});

async function uploadFile(input, endpoint) {
  if (!input.files.length) return;
  const data = new FormData();
  data.append("file", input.files[0]);
  await api(endpoint, { method: "POST", body: data, headers: {} });
  showAlert("File uploaded.");
  refreshProfile();
}

$("#resumeUpload").addEventListener("change", (event) => uploadFile(event.target, "/profiles/applicant/resume").catch((error) => showAlert(error.message, "danger")));
$("#imageUpload").addEventListener("change", (event) => uploadFile(event.target, "/profiles/applicant/image").catch((error) => showAlert(error.message, "danger")));

loadSession();
