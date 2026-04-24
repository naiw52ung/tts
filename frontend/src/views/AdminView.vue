<script setup lang="ts">
import { ref } from "vue";
import { ElMessage } from "element-plus";
import { getAdminFailuresSummary, getAdminOrders, getAdminOverview, getAdminTasks, getAdminUsers, mockPayOrder } from "../api/admin";

const adminKey = ref(localStorage.getItem("admin_key") ?? "");
const loading = ref(false);
const taskStatusFilter = ref("");
const overview = ref<any | null>(null);
const users = ref<any[]>([]);
const tasks = ref<any[]>([]);
const failures = ref<any | null>(null);
const orders = ref<any[]>([]);

async function refreshAll() {
  if (!adminKey.value) {
    ElMessage.error("请先输入 ADMIN_API_KEY");
    return;
  }
  loading.value = true;
  try {
    localStorage.setItem("admin_key", adminKey.value);
    overview.value = await getAdminOverview(adminKey.value);
    users.value = await getAdminUsers(adminKey.value, 50);
    tasks.value = await getAdminTasks(adminKey.value, taskStatusFilter.value, 100);
    failures.value = await getAdminFailuresSummary(adminKey.value, 300);
    orders.value = await getAdminOrders(adminKey.value, "", 100);
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "管理员接口请求失败");
  } finally {
    loading.value = false;
  }
}

async function markOneOrderPaid(orderNo: string) {
  if (!adminKey.value) {
    ElMessage.error("请先输入 ADMIN_API_KEY");
    return;
  }
  await mockPayOrder(adminKey.value, orderNo);
  ElMessage.success(`订单 ${orderNo} 已标记支付成功`);
  await refreshAll();
}
</script>

<template>
  <el-card>
    <h3>管理后台 V1（只读）</h3>
    <el-form label-width="140px">
      <el-form-item label="ADMIN_API_KEY">
        <el-input v-model="adminKey" type="password" show-password style="max-width: 460px" />
      </el-form-item>
      <el-form-item label="任务状态筛选">
        <el-select v-model="taskStatusFilter" clearable style="width: 220px">
          <el-option label="pending" value="pending" />
          <el-option label="processing" value="processing" />
          <el-option label="cancelling" value="cancelling" />
          <el-option label="cancelled" value="cancelled" />
          <el-option label="success" value="success" />
          <el-option label="failed" value="failed" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="refreshAll">刷新后台数据</el-button>
      </el-form-item>
    </el-form>
  </el-card>

  <el-card style="margin-top: 12px">
    <h3>概览</h3>
    <el-descriptions v-if="overview" :column="3" border>
      <el-descriptions-item label="总用户">{{ overview.total_users }}</el-descriptions-item>
      <el-descriptions-item label="总任务">{{ overview.total_tasks }}</el-descriptions-item>
      <el-descriptions-item label="处理中任务">{{ overview.pending_tasks }}</el-descriptions-item>
      <el-descriptions-item label="失败任务">{{ overview.failed_tasks }}</el-descriptions-item>
      <el-descriptions-item label="已支付订单">{{ overview.paid_orders }}</el-descriptions-item>
      <el-descriptions-item label="累计充值">{{ overview.total_recharge }}</el-descriptions-item>
    </el-descriptions>
    <p v-else>暂无数据，请先输入管理员密钥并刷新。</p>
  </el-card>

  <el-card style="margin-top: 12px">
    <h3>用户列表（最新50）</h3>
    <el-table :data="users" max-height="320">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="email" label="邮箱" />
      <el-table-column prop="balance" label="余额" width="100" />
      <el-table-column prop="created_at" label="创建时间" width="220" />
    </el-table>
  </el-card>

  <el-card style="margin-top: 12px">
    <h3>任务列表（最新100）</h3>
    <el-table :data="tasks" max-height="360">
      <el-table-column prop="id" label="任务ID" width="80" />
      <el-table-column prop="user_id" label="用户ID" width="80" />
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column prop="progress" label="进度" width="90" />
      <el-table-column prop="req_doc_text" label="需求" />
      <el-table-column prop="error_msg" label="错误信息" width="220" />
    </el-table>
  </el-card>

  <el-card style="margin-top: 12px">
    <h3>充值订单（最新100）</h3>
    <el-table :data="orders" max-height="320">
      <el-table-column prop="order_no" label="订单号" />
      <el-table-column prop="user_email" label="用户" width="220" />
      <el-table-column prop="amount" label="金额" width="100" />
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column prop="created_at" label="创建时间" width="220" />
      <el-table-column label="操作" width="130">
        <template #default="scope">
          <el-button
            v-if="scope.row.status === 'pending'"
            size="small"
            type="success"
            @click="markOneOrderPaid(scope.row.order_no)"
          >
            模拟支付成功
          </el-button>
          <span v-else>-</span>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-card style="margin-top: 12px">
    <h3>失败原因统计（最近300条失败任务样本）</h3>
    <el-table :data="failures?.top_reasons ?? []" max-height="280">
      <el-table-column prop="reason" label="错误前缀" />
      <el-table-column prop="count" label="次数" width="120" />
    </el-table>
    <h4 style="margin-top: 10px">近期失败样本（20条）</h4>
    <el-table :data="failures?.recent_failed_samples ?? []" max-height="260">
      <el-table-column prop="task_id" label="任务ID" width="90" />
      <el-table-column prop="user_id" label="用户ID" width="90" />
      <el-table-column prop="error_msg" label="错误详情" />
      <el-table-column prop="created_at" label="时间" width="220" />
    </el-table>
  </el-card>
</template>
