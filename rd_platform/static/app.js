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
    await refreshLifecycle();
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
  renderSelect(byId("lifecycle-project"), snapshot.projects, "项目");
  renderSelect(byId("control-task"), snapshot.tasks, "任务");
  renderProjects(); renderAgents(); renderEvents();
}

let lifecycleRequest = 0;
async function refreshLifecycle() {
  const generation = ++lifecycleRequest;
  const projectId = byId("lifecycle-project").value;
  const status = byId("lifecycle-status");
  ["lifecycle-summary", "lifecycle-gates", "lifecycle-details"].forEach((id) => clear(byId(id)));
  if (!projectId) { status.textContent = "尚无项目。"; return; }
  try {
    const response = await fetch(`/api/lifecycle?project_id=${encodeURIComponent(projectId)}`, { cache: "no-store" });
    const data = await response.json();
    if (generation !== lifecycleRequest) return;
    if (!response.ok) { status.textContent = `生命周期未就绪：${data.error || "读取失败"}`; return; }
    const lifecycle = data.lifecycle;
    status.textContent = `${lifecycle.state} · 当前阶段 ${lifecycle.current_gate} · 已作出决策 ${lifecycle.progress.decided}/${lifecycle.progress.total}（不代表全部通过）`;
    [["版本化产物", data.summary.artifacts], ["追踪缺口", data.summary.trace_gaps], ["未关闭缺陷", data.summary.open_defects]].forEach(([label, count]) => {
      const block = element("div", undefined, "counter"); block.append(element("strong", count), element("span", label)); byId("lifecycle-summary").append(block);
    });
    data.gates.slice().sort((a, b) => a.ordinal - b.ordinal).forEach((gate) => {
      const row = element("tr"); [gate.gate_id, gate.evaluation_state, gate.gate_status || "未作出结论", gate.current_assessment_id || "无"].forEach((value) => row.append(element("td", value))); byId("lifecycle-gates").append(row);
    });
    const sections = [["待处理事项", data.next_actions], ["工作单与租约", data.work_orders], ["需求追踪", data.traceability], ["测试模型", data.test_models], ["测试用例", data.test_cases], ["真实测试执行", data.test_executions], ["缺陷闭环", data.defects], ["版本化产物", data.artifacts], ["发布记录", data.releases], ["生命周期事件", data.events]];
    sections.forEach(([label, rows]) => {
      const details = element("details", undefined, "run-details"); details.append(element("summary", `${label}（本页 ${rows.length} 项）`), element("pre", JSON.stringify(rows, null, 2))); byId("lifecycle-details").append(details);
    });
    if (data.has_more || Object.values(data.collections_truncated).some(Boolean)) byId("lifecycle-details").prepend(element("p", "数据已截页；使用 CLI lifecycle 查看事件后续，使用 lifecycle-collection 的游标查看各集合后续。不能把本页数量当作完整数量。", "table-note"));
  } catch (error) { if (generation === lifecycleRequest) status.textContent = `生命周期读取失败：${error.message}`; }
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

function renderAgents() {
  const root = byId("agents"); clear(root);
  if (!snapshot.agents.length) { const row = element("tr"); const cell = element("td", "尚未登记 Agent。", "empty"); cell.colSpan = 5; row.append(cell); root.append(row); return; }
  const tasks = new Map(snapshot.tasks.map((task) => [task.id, task]));
  snapshot.agents.forEach((agent) => {
    const row = element("tr"); const task = tasks.get(agent.task_id); const work = agent.current_work;
    let heartbeat = work?.heartbeat_at || agent.heartbeat_at || "未报告";
    if ((agent.status === "BUSY" || work?.lease_until) && Date.now() - Date.parse(heartbeat) > 300000) heartbeat = `可能失联（最后报告 ${heartbeat}）`;
    [agent.id, agent.role, agent.effective_status || agent.status || "未记录"].forEach((v) => row.append(element("td", v)));
    const content = element("td");
    if (work) {
      content.append(element("p", `${work.gate_id} · ${work.id} · ${work.activity}`), element("p", `原因：${work.why}`),
        element("p", `进度：${work.progress_percent === null ? "未报告百分比" : `${work.progress_percent}%`}；版本 ${work.version} / 尝试 ${work.attempt}`));
      if (work.blocked_reason) content.append(element("p", `需处理：${work.blocked_reason}`));
      const details = element("details"); details.append(element("summary", "输入、输出与下一次交接"),
        element("pre", JSON.stringify({ inputs: work.input_refs, outputs: work.output_refs || [], next: work.next_handoff }, null, 2)));
      content.append(details);
    } else content.textContent = task ? `${task.id} · ${task.title}` : (agent.task_id || "无");
    row.append(content, element("td", heartbeat)); root.append(row);
  });
}

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
bindForm("lifecycle-control-form", "lifecycle.control", (data) => ({...data, project_id: byId("lifecycle-project").value}));
bindForm("work-control-form", "work.control", (data) => { if (!data.agent_id) delete data.agent_id; return data; });
bindForm("agent-form", "agent.register", (data) => data);
bindForm("task-form", "task.create", (data) => ({ ...data, requirements: lines(data.requirements), dependencies: lines(data.dependencies), inputs: JSON.parse(data.inputs || "{}") }));
bindForm("control-form", "task.control", (data) => {
  ["agent_id", "title", "why"].forEach((key) => { if (!data[key]) delete data[key]; }); return data;
});
byId("refresh").addEventListener("click", refresh);
byId("lifecycle-project").addEventListener("change", refreshLifecycle);
function autoRefresh() {
  if (document.hidden) return;
  // Preserve open evidence and partially entered controls. The explicit
  // refresh button remains available when the reader wants a new snapshot.
  if (document.querySelector("details[open]")) {
    byId("refresh-status").textContent = "正在查看展开内容，自动刷新暂缓；可手动刷新，收起后恢复。";
    return;
  }
  refresh();
}
setInterval(autoRefresh, 3000);
document.addEventListener("visibilitychange", autoRefresh);
refresh();
