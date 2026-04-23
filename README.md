# LegendAI Builder Prototype

最小可运行闭环原型：
- 注册/登录（JWT）
- 上传版本包 + 自然语言需求
- 异步任务队列处理（Celery）
- MonItems 爆率修改
- 任务进度与 SSE 日志
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
