<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { createPaymentOrder, listPaymentOrders } from "../api/payments";
import { cancelTask, createTask, dryRunTask, listTasks, listTemplates, taskDownloadUrl } from "../api/tasks";
import { getMe } from "../api/users";

const engine = ref("GOM");
const versionType = ref("复古");
const reqDocText = ref("将全部怪物爆率提升20%");
const selectedTemplateId = ref<number | null>(null);
const file = ref<File | null>(null);
const tasks = ref<any[]>([]);
const templates = ref<any[]>([]);
const meInfo = ref<any | null>(null);
const paymentAmount = ref(30);
const orders = ref<any[]>([]);
const pendingOrderSet = ref<Set<string>>(new Set());
const creating = ref(false);
const previewing = ref(false);
const previewDialogVisible = ref(false);
const previewResult = ref<any | null>(null);
const selectedTaskId = ref<number | null>(null);
const liveLogs = ref("");
let currentEventSource: EventSource | null = null;

function onFileChange(uploadFile: any) {
  file.value = uploadFile.raw;
}

async function refreshTasks() {
  tasks.value = await listTasks();
}

async function refreshMe() {
  meInfo.value = await getMe();
}

async function refreshTemplates() {
  templates.value = await listTemplates();
}

async function refreshOrders() {
  orders.value = await listPaymentOrders();
  const latestPending = new Set<string>(
    orders.value.filter((item: any) => item.status === "pending").map((item: any) => item.order_no)
  );
  const previousPending = pendingOrderSet.value;
  let hasPaidNow = false;
  for (const orderNo of previousPending) {
    if (!latestPending.has(orderNo)) {
      const found = orders.value.find((item: any) => item.order_no === orderNo);
      if (found?.status === "paid") {
        hasPaidNow = true;
      }
    }
  }
  pendingOrderSet.value = latestPending;
  if (hasPaidNow) {
    ElMessage.success("检测到充值到账，余额已更新");
    await refreshMe();
  }
}

function onTemplateChange(templateId: number | null) {
  if (!templateId) {
    return;
  }
  const target = templates.value.find((item) => item.id === templateId);
  if (target) {
    reqDocText.value = target.default_requirement;
  }
}

async function runDryPreview() {
  if (!file.value) {
    ElMessage.error("请先上传版本包");
    return;
  }
  previewing.value = true;
  try {
    previewResult.value = await dryRunTask({
      engine: engine.value,
      versionType: versionType.value,
      reqDocText: reqDocText.value,
      templateId: selectedTemplateId.value,
      file: file.value
    });
    previewDialogVisible.value = true;
    ElMessage.success(`预览完成，共 ${previewResult.value.change_count} 处变更`);
  } finally {
    previewing.value = false;
  }
}

async function submitTask() {
  if (!file.value) {
    ElMessage.error("请先上传版本包");
    return;
  }
  creating.value = true;
  try {
    await createTask({
      engine: engine.value,
      versionType: versionType.value,
      reqDocText: reqDocText.value,
      templateId: selectedTemplateId.value,
      file: file.value
    });
    ElMessage.success("任务已提交");
    await refreshMe();
    await refreshTasks();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "任务提交失败");
  } finally {
    creating.value = false;
  }
}

async function cancelOneTask(taskId: number) {
  await cancelTask(taskId);
  ElMessage.success("取消请求已提交");
  await refreshTasks();
}

async function createOrder() {
  if (paymentAmount.value <= 0) {
    ElMessage.error("充值金额必须大于 0");
    return;
  }
  const result = await createPaymentOrder(paymentAmount.value, "workbench_topup");
  ElMessage.success(`充值订单已创建：${result.order_no}`);
  await refreshOrders();
}

onMounted(async () => {
  await refreshMe();
  await refreshOrders();
  await refreshTemplates();
  await refreshTasks();
  setInterval(refreshTasks, 2000);
  setInterval(refreshMe, 5000);
  setInterval(refreshOrders, 7000);
});

function watchLogs(taskId: number) {
  if (currentEventSource) {
    currentEventSource.close();
    currentEventSource = null;
  }
  selectedTaskId.value = taskId;
  liveLogs.value = "";
  const token = localStorage.getItem("token");
  currentEventSource = new EventSource(
    `http://localhost:8000/api/v1/tasks/${taskId}/logs?token=${token ?? ""}`
  );
  currentEventSource.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    liveLogs.value += payload.delta;
  };
  currentEventSource.addEventListener("end", () => {
    currentEventSource?.close();
    currentEventSource = null;
  });
}
</script>

<template>
  <el-card style="margin-bottom: 12px">
    <h3>账户信息</h3>
    <p>当前余额：{{ meInfo?.balance ?? "-" }} 点</p>
    <p>每次任务扣费：{{ meInfo?.task_cost ?? "-" }} 点</p>
  </el-card>

  <el-card style="margin-bottom: 12px">
    <h3>充值订单（支付骨架）</h3>
    <el-space>
      <el-input-number v-model="paymentAmount" :min="1" :step="10" />
      <el-button type="primary" @click="createOrder">创建充值订单</el-button>
    </el-space>
    <el-table :data="orders" max-height="220" style="margin-top: 10px">
      <el-table-column prop="order_no" label="订单号" />
      <el-table-column prop="amount" label="金额" width="100" />
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column prop="channel" label="渠道" width="100" />
      <el-table-column prop="created_at" label="创建时间" width="220" />
    </el-table>
    <p style="margin-top: 8px; color: #999">说明：V1 为 mock 支付，需在管理员后台手动触发“支付成功回调”。</p>
  </el-card>

  <el-card>
    <h3>创建任务</h3>
    <el-form label-width="120px">
      <el-form-item label="引擎">
        <el-select v-model="engine" style="width: 200px">
          <el-option label="GOM" value="GOM" />
          <el-option label="GEE" value="GEE" />
        </el-select>
      </el-form-item>
      <el-form-item label="版本类型">
        <el-input v-model="versionType" style="max-width: 300px" />
      </el-form-item>
      <el-form-item label="需求文档">
        <el-input v-model="reqDocText" type="textarea" :rows="4" />
      </el-form-item>
      <el-form-item label="模板">
        <el-select
          v-model="selectedTemplateId"
          clearable
          placeholder="可选：选择模板自动填充需求"
          style="width: 360px"
          @change="onTemplateChange"
        >
          <el-option
            v-for="item in templates"
            :key="item.id"
            :label="`${item.name}（${item.engine}）`"
            :value="item.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="版本包">
        <el-upload :limit="1" :auto-upload="false" :on-change="onFileChange">
          <el-button>选择 ZIP/RAR/7z</el-button>
        </el-upload>
      </el-form-item>
      <el-form-item>
        <el-button :loading="previewing" @click="runDryPreview">Dry Run 预览</el-button>
        <el-button type="primary" :loading="creating" @click="submitTask">提交任务</el-button>
      </el-form-item>
    </el-form>
  </el-card>

  <el-card style="margin-top: 12px">
    <el-space style="margin-bottom: 8px">
      <h3>任务列表</h3>
      <el-button size="small" @click="refreshTasks">刷新</el-button>
    </el-space>
    <el-table :data="tasks">
      <el-table-column prop="id" label="任务ID" width="80" />
      <el-table-column prop="status" label="状态" width="120" />
      <el-table-column prop="progress" label="进度">
        <template #default="scope">
          <el-progress :percentage="scope.row.progress" />
        </template>
      </el-table-column>
      <el-table-column prop="req_doc_text" label="需求" />
      <el-table-column label="操作" width="220">
        <template #default="scope">
          <el-button size="small" @click="watchLogs(scope.row.id)">查看日志</el-button>
          <el-button
            v-if="['pending', 'processing', 'cancelling'].includes(scope.row.status)"
            size="small"
            type="warning"
            plain
            @click="cancelOneTask(scope.row.id)"
          >
            取消任务
          </el-button>
          <a v-if="scope.row.status === 'success'" :href="taskDownloadUrl(scope.row.id)" target="_blank">下载输出包</a>
          <span v-else>-</span>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-card style="margin-top: 12px">
    <h3>实时日志（任务 {{ selectedTaskId ?? "-" }}）</h3>
    <el-input :model-value="liveLogs" type="textarea" :rows="10" readonly />
  </el-card>

  <el-dialog v-model="previewDialogVisible" title="Dry Run 预览结果" width="70%">
    <div v-if="previewResult">
      <p>解析目标：{{ previewResult.instruction.target_keyword }}</p>
      <p>调整幅度：{{ previewResult.instruction.change_percent }}%</p>
      <p>预计变更：{{ previewResult.change_count }} 处</p>
      <el-table :data="previewResult.changes" max-height="360">
        <el-table-column prop="target_file" label="文件" />
        <el-table-column prop="old_content" label="原内容" />
        <el-table-column prop="new_content" label="新内容" />
      </el-table>
    </div>
  </el-dialog>
</template>
