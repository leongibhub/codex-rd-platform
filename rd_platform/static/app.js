"use strict";

let snapshot = { projects: [], agents: [], tasks: [], runs: [], events: [], defects: [] };
let refreshInFlight = false;
const byId = (id) => document.getElementById(id);

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = String(text);
  if (className) node.className = className;
  return node;
}

function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }
function lines(value) { return value.split("\n").map((v) => v.trim()).filter(Boolean); }

async function api(command, data) {
  const response = await fetch("/api/commands", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ command, data, request_id: crypto.randomUUID() }),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "控制请求失败");
  return result;
}

async function refresh() {
  if (refreshInFlight) return;
  refreshInFlight = true;
  try {
    const response = await fetch("/api/snapshot", { cache: "no-store" });
    if (!response.ok) throw new Error("无法读取本地快照");
    snapshot = await response.json();
    render();
    const now = new Date().toLocaleTimeString("zh-CN", { hour12: false });
    byId("refresh-status").textContent = `每 3 秒在可见页面自动刷新。最后成功：${now}`;
    notice("已更新：仅显示已持久化的运行事实。", false);
  } catch (error) { byId("refresh-status").textContent = "自动刷新断连；将于页面可见时重试。"; notice(error.message, true); }
  finally { refreshInFlight = false; }
}

function notice(message, isError) {
  const target = byId("notice");
  target.textContent = message;
  target.classList.toggle("error", Boolean(isError));
}

function renderSelect(select, rows, label) {
  const selected = select.value;
  clear(select);
  if (!rows.length) {
    const option = element("option", `先创建${label}`); option.value = ""; select.append(option); return;
  }
  rows.forEach((row) => { const option = element("option", `${row.id} · ${row.name || row.title}`); option.value = row.id; select.append(option); });
  if (rows.some((row) => row.id === selected)) select.value = selected;
}

function render() {
  const counters = byId("counters"); clear(counters);
  [["项目", snapshot.projects.length], ["任务", snapshot.tasks.length], ["运行", snapshot.runs.length], ["缺陷", snapshot.defects.length]].forEach(([label, count]) => {
    const block = element("div", undefined, "counter"); block.append(element("strong", count), element("span", label)); counters.append(block);
  });
  renderSelect(byId("task-project"), snapshot.projects, "项目");
  renderSelect(byId("control-task"), snapshot.tasks, "任务");
  renderProjects(); renderAgents(); renderEvents();
}

function renderProjects() {
  const root = byId("projects"); clear(root);
  if (!snapshot.projects.length) { root.append(byId("empty-template").content.cloneNode(true)); return; }
  snapshot.projects.forEach((project) => {
    const card = element("article", undefined, "project-card");
    const header = element("header");
    const title = element("div"); title.append(element("p", project.id, "eyebrow"), element("h3", project.name));
    header.append(title, element("span", `项目运行状态：${project.stage || "未设"}`, "status")); card.append(header, element("p", project.idea, "idea"));
    const tasks = snapshot.tasks.filter((task) => task.project_id === project.id);
    if (!tasks.length) card.append(element("p", "该项目尚无任务。", "empty"));
    tasks.forEach((task) => card.append(renderTask(task)));
    root.append(card);
  });
}

function renderTask(task) {
  const article = element("article", undefined, "task");
  const head = element("div", undefined, "task-head");
  const left = element("div"); left.append(element("p", task.id, "mono"), element("h4", task.title));
  const status = element("span", task.status || "UNKNOWN", "status"); head.append(left, status); article.append(head);
  const why = element("p", task.why, "why"); article.append(why);
  const facts = element("dl", undefined, "facts");
  [["角色", task.role], ["当前质量阶段", task.next_phase], ["检查", `${task.checks_passed ?? 0}/${task.checks_total ?? 0}`], ["版本", task.revision], ["依赖", (task.dependencies || []).join("、") || "无"]].forEach(([label, value]) => {
    facts.append(element("dt", label), element("dd", value || "未记录"));
  }); article.append(facts);
  const io = element("div", undefined, "io");
  io.append(element("p", `输入：${JSON.stringify(task.inputs || {})}`), element("p", `需求：${(task.requirements || []).join("；") || "未记录"}`)); article.append(io);
  const relatedRuns = snapshot.runs.filter((run) => run.task_id === task.id);
  if (relatedRuns.length) { article.append(element("p", `交接/运行：${relatedRuns.map((run) => `${run.phase}:${run.status}`).join(" → ")}`, "handoff")); const details = element("details", undefined, "run-details"); details.append(element("summary", `查看 ${relatedRuns.length} 条实际运行摘要与证据`)); relatedRuns.forEach((run) => { const record = element("section", undefined, "run-record"); record.append(element("h5", `${run.phase || "未记录阶段"} · ${run.status || "未记录状态"}`), element("p", `执行者：${run.agent_id || "未记录"}；摘要：${run.summary || "未报告"}`)); if (run.evidence) record.append(element("pre", JSON.stringify(run.evidence, null, 2))); details.append(record); }); article.append(details); }
  return article;
}

function renderAgents() { const root = byId("agents"); clear(root); if (!snapshot.agents.length) { const row = element("tr"); const cell = element("td", "尚未登记 Agent。", "empty"); cell.colSpan = 5; row.append(cell); root.append(row); return; } const tasks = new Map(snapshot.tasks.map((task) => [task.id, task])); snapshot.agents.forEach((agent) => { const row = element("tr"); const task = tasks.get(agent.task_id); let heartbeat = agent.heartbeat_at || "未报告"; if (agent.status === "BUSY" && agent.heartbeat_at && Date.now() - Date.parse(agent.heartbeat_at) > 300000) heartbeat = `可能失联（最后报告 ${agent.heartbeat_at}）`; [agent.id, agent.role, agent.status || "未记录", task ? `${task.id} · ${task.title}` : (agent.task_id || "无"), heartbeat].forEach((value) => row.append(element("td", value))); root.append(row); }); }

function renderEvents() {
  const root = byId("events"); clear(root);
  if (!snapshot.events.length) { root.append(element("li", "尚无事件；创建或控制操作后会在此显示。", "empty")); return; }
  snapshot.events.slice().reverse().forEach((event) => {
    const item = element("li");
    item.append(element("time", event.created_at || "时间未记录"), element("strong", event.type || "事件"), element("p", `项目 ${event.project_id || "—"} · 任务 ${event.task_id || "—"} · 运行 ${event.run_id || "—"}`));
    if (event.data && Object.keys(event.data).length) item.append(element("pre", JSON.stringify(event.data, null, 2)));
    root.append(item);
  });
}

function formData(form) { return Object.fromEntries(new FormData(form).entries()); }
function bindForm(id, command, convert) {
  byId(id).addEventListener("submit", async (event) => {
    event.preventDefault();
    // currentTarget is intentionally only populated while an event listener
    // runs; retain the form before the first await.
    const form = event.currentTarget;
    try { await api(command, convert(formData(form))); form.reset(); await refresh(); }
    catch (error) { notice(error.message, true); }
  });
}

bindForm("project-form", "project.create", (data) => data);
bindForm("agent-form", "agent.register", (data) => data);
bindForm("task-form", "task.create", (data) => ({ ...data, requirements: lines(data.requirements), dependencies: lines(data.dependencies), inputs: JSON.parse(data.inputs || "{}") }));
bindForm("control-form", "task.control", (data) => {
  ["agent_id", "title", "why"].forEach((key) => { if (!data[key]) delete data[key]; }); return data;
});
byId("refresh").addEventListener("click", refresh);
setInterval(() => { if (!document.hidden) refresh(); }, 3000);
document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
refresh();
