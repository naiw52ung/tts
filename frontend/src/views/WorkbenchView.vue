<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { createTask, listTasks, taskDownloadUrl } from "../api/tasks";

const engine = ref("GOM");
const versionType = ref("复古");
const reqDocText = ref("将全部怪物爆率提升20%");
const file = ref<File | null>(null);
const tasks = ref<any[]>([]);
const creating = ref(false);
const selectedTaskId = ref<number | null>(null);
const liveLogs = ref("");
let currentEventSource: EventSource | null = null;

function onFileChange(uploadFile: any) {
  file.value = uploadFile.raw;
}

async function refreshTasks() {
  tasks.value = await listTasks();
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
      file: file.value
    });
    ElMessage.success("任务已提交");
    await refreshTasks();
  } finally {
    creating.value = false;
  }
}

onMounted(async () => {
  await refreshTasks();
  setInterval(refreshTasks, 2000);
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
      <el-form-item label="版本包">
        <el-upload :limit="1" :auto-upload="false" :on-change="onFileChange">
          <el-button>选择 ZIP/RAR/7z</el-button>
        </el-upload>
      </el-form-item>
      <el-form-item>
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
</template>
