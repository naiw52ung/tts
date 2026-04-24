import api from "./client";

function withAdminKey(adminKey: string) {
  return {
    headers: {
      "X-Admin-Key": adminKey
    }
  };
}

export async function getAdminOverview(adminKey: string) {
  const { data } = await api.get("/admin/overview", withAdminKey(adminKey));
  return data;
}

export async function getAdminUsers(adminKey: string, limit = 50) {
  const { data } = await api.get("/admin/users", {
    ...withAdminKey(adminKey),
    params: { limit }
  });
  return data;
}

export async function getAdminTasks(adminKey: string, status = "", limit = 100) {
  const { data } = await api.get("/admin/tasks", {
    ...withAdminKey(adminKey),
    params: { status: status || undefined, limit }
  });
  return data;
}

export async function getAdminFailuresSummary(adminKey: string, limit = 200) {
  const { data } = await api.get("/admin/failures-summary", {
    ...withAdminKey(adminKey),
    params: { limit }
  });
  return data;
}

export async function getAdminOrders(adminKey: string, status = "", limit = 100) {
  const { data } = await api.get("/admin/orders", {
    ...withAdminKey(adminKey),
    params: { status: status || undefined, limit }
  });
  return data;
}

export async function mockPayOrder(adminKey: string, orderNo: string) {
  const { data } = await api.post(
    `/payments/orders/${orderNo}/mock-paid`,
    {},
    {
      headers: {
        "X-Admin-Key": adminKey
      }
    }
  );
  return data;
}
