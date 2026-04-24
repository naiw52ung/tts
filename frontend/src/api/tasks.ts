import api from "./client";

export async function createTask(payload: {
  engine: string;
  versionType: string;
  reqDocText?: string;
  templateId?: number | null;
  file: File;
}) {
  const form = new FormData();
  form.append("engine", payload.engine);
  form.append("version_type", payload.versionType);
  if (payload.reqDocText) {
    form.append("req_doc_text", payload.reqDocText);
  }
  if (payload.templateId) {
    form.append("template_id", String(payload.templateId));
  }
  form.append("version_file", payload.file);
  const { data } = await api.post("/tasks", form);
  return data;
}

export async function listTemplates() {
  const { data } = await api.get("/tasks/templates");
  return data;
}

export async function dryRunTask(payload: {
  engine: string;
  versionType: string;
  reqDocText?: string;
  templateId?: number | null;
  file: File;
}) {
  const form = new FormData();
  form.append("engine", payload.engine);
  form.append("version_type", payload.versionType);
  if (payload.reqDocText) {
    form.append("req_doc_text", payload.reqDocText);
  }
  if (payload.templateId) {
    form.append("template_id", String(payload.templateId));
  }
  form.append("version_file", payload.file);
  const { data } = await api.post("/tasks/dry-run", form);
  return data;
}

export async function listTasks() {
  const { data } = await api.get("/tasks");
  return data;
}

export async function getTask(taskId: number) {
  const { data } = await api.get(`/tasks/${taskId}`);
  return data;
}

export async function cancelTask(taskId: number) {
  const { data } = await api.post(`/tasks/${taskId}/cancel`);
  return data;
}

export function taskDownloadUrl(taskId: number): string {
  const base = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
  return `${base}/tasks/${taskId}/download`;
}
