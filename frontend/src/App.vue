<script setup lang="ts">
import { ref } from "vue";
import { ElMessage } from "element-plus";
import { login, register } from "./api/auth";
import AdminView from "./views/AdminView.vue";
import WorkbenchView from "./views/WorkbenchView.vue";

const email = ref("");
const password = ref("");
const hasToken = ref(!!localStorage.getItem("token"));
const loading = ref(false);
const activePanel = ref<"workbench" | "admin">("workbench");

async function doLogin() {
  loading.value = true;
  try {
    const data = await login(email.value, password.value);
    localStorage.setItem("token", data.access_token);
    hasToken.value = true;
    ElMessage.success("登录成功");
  } finally {
    loading.value = false;
  }
}

async function doRegister() {
  loading.value = true;
  try {
    const data = await register(email.value, password.value);
    localStorage.setItem("token", data.access_token);
    hasToken.value = true;
    ElMessage.success("注册成功");
  } finally {
    loading.value = false;
  }
}

function logout() {
  localStorage.removeItem("token");
  hasToken.value = false;
}
</script>

<template>
  <div style="max-width: 980px; margin: 20px auto; padding: 0 12px">
    <h2>LegendAI Builder 原型</h2>
    <template v-if="!hasToken">
      <el-card>
        <el-form label-width="80px">
          <el-form-item label="邮箱">
            <el-input v-model="email" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="password" type="password" show-password />
          </el-form-item>
        </el-form>
        <el-space>
          <el-button type="primary" :loading="loading" @click="doLogin">登录</el-button>
          <el-button :loading="loading" @click="doRegister">注册并登录</el-button>
        </el-space>
      </el-card>
    </template>
    <template v-else>
      <el-space style="margin-bottom: 12px">
        <el-button type="danger" plain @click="logout">退出登录</el-button>
        <el-button :type="activePanel === 'workbench' ? 'primary' : 'default'" @click="activePanel = 'workbench'">
          工作台
        </el-button>
        <el-button :type="activePanel === 'admin' ? 'primary' : 'default'" @click="activePanel = 'admin'">
          管理后台
        </el-button>
      </el-space>
      <WorkbenchView v-if="activePanel === 'workbench'" />
      <AdminView v-else />
    </template>
  </div>
</template>
