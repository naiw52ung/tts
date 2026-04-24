# LegendAI Builder Prototype

最小可运行闭环原型：
- 注册/登录（JWT）
- 上传版本包 + 自然语言需求
- 模板化输入 + Dry Run 预览
- 异步任务队列处理（Celery）
- MonItems 爆率修改
- 任务进度与 SSE 日志
- 任务取消（pending/processing）
- 余额扣费账本 + 充值订单 mock 回调
- 管理后台只读看板（用户/任务/失败原因）
- 输出包下载

## 1. 启动

```bash
cp .env.example .env
docker compose up --build
```

服务地址：
- 前端：http://localhost:5173
- 后端：http://localhost:8000/docs

## 1.1 无 Docker 本地启动（推荐你当前环境）

```bash
cd /Users/a123/legendai-builder
chmod +x scripts/local_up.sh scripts/local_down.sh scripts/verify_local_api.sh
./scripts/local_up.sh
```

本地模式说明：
- 数据库使用 SQLite：`backend/legendai_local.db`
- Celery 使用 eager 模式（不依赖 Redis/Worker 进程）
- 存储目录：`backend/local_storage`

停止服务：

```bash
./scripts/local_down.sh
```

快速接口验收：

```bash
./scripts/verify_local_api.sh
```

说明：新版 `verify_local_api.sh` 会覆盖模板、dry-run、支付订单、mock 回调、任务执行与下载闭环。

## 2. 演示数据准备

1. 本地创建目录 `MonItems/`，放入一个或多个 `*.txt`（可参考 `examples/MonItems_Demo.txt`）。
2. 将这个目录压缩成 `zip`（原型支持 zip/rar/7z）。
3. 在前端上传并输入需求，例如：`将全部怪物爆率提升20%`。

## 3. 后端结构

- `backend/app/api/v1/auth.py`：注册/登录
- `backend/app/api/v1/tasks.py`：任务提交、状态查询、SSE、下载
- `backend/app/worker/tasks.py`：任务执行主链路
- `backend/app/services/legend_modifier.py`：爆率文本修改
- `backend/app/services/llm_parser.py`：LLM 解析 + fallback

## 4. 测试

```bash
cd backend
pip install -r requirements.txt
pytest
```

## 5. 注意事项

- 若未配置 `DEEPSEEK_API_KEY`，系统自动使用规则解析需求。
- 当前原型仅对 GOM/GEE + 爆率修改做最小实现。
- 生产环境需补充病毒扫描、容器隔离、配额与计费策略。
- 如需使用管理员接口（充值、后台、mock 支付回调），请在环境变量中配置 `ADMIN_API_KEY`。

## 6. 生产部署文件

已提供生产部署所需文件：
- `docker-compose.prod.yml`
- `.env.prod.example`
- `frontend/Dockerfile.prod`
- `deploy/nginx/conf.d/default.conf`
- `scripts/deploy_prod.sh`

快速部署：

```bash
cp .env.prod.example .env.prod
# 编辑 .env.prod，填入数据库密码/SECRET_KEY/API_KEY
chmod +x scripts/deploy_prod.sh
./scripts/deploy_prod.sh
```

常用命令：

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
docker compose --env-file .env.prod -f docker-compose.prod.yml logs -f api
docker compose --env-file .env.prod -f docker-compose.prod.yml logs -f worker
docker compose --env-file .env.prod -f docker-compose.prod.yml down
```

## 7. 备份与恢复（V1）

生产脚本：
- `scripts/backup_prod.sh`：备份 PostgreSQL + `/data/storage`
- `scripts/restore_prod.sh <backup_dir>`：从指定备份恢复

使用方式：

```bash
chmod +x scripts/backup_prod.sh scripts/restore_prod.sh
./scripts/backup_prod.sh
# 生成目录：./backups/<timestamp>

./scripts/restore_prod.sh ./backups/<timestamp>
```

可选环境变量（写在 `.env.prod` 或执行前导出）：
- `BACKUP_ROOT`：备份根目录（默认 `./backups`）
- `BACKUP_KEEP_DAYS`：保留天数（默认 `7`）

## 8. 线上验收清单（发布后）

部署完成后可按以下顺序快速验收：

1) 基础健康检查

```bash
curl http://2tt2.com/api/health
```

2) 用户链路（注册 -> 模板 -> dry-run -> 提交任务）
- 前端登录后在工作台选择模板
- 点击 `Dry Run 预览`，确认有变更明细
- 提交任务并确认任务最终 `success`

3) 计费链路（下单 -> 模拟回调 -> 余额变化）
- 工作台创建充值订单
- 管理后台订单列表点击 `模拟支付成功`
- 返回工作台确认余额自动刷新

4) 管理后台链路
- 输入 `ADMIN_API_KEY` 后刷新看板
- 检查概览、任务、订单、失败原因统计是否有数据

5) 备份与回滚演练

```bash
cd /www/wwwroot/legendai-builder
./scripts/backup_prod.sh
ls -la backups
# 如需回滚：
# ./scripts/restore_prod.sh ./backups/<timestamp>
```
