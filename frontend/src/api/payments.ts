import api from "./client";

export async function createPaymentOrder(amount: number, remark = "manual_topup", channel = "mock") {
  const { data } = await api.post("/payments/orders", { amount, remark, channel });
  return data;
}

export async function listPaymentOrders() {
  const { data } = await api.get("/payments/orders");
  return data;
}
