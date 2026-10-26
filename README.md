# 校园在线学习平台

基于 FastAPI、Vue 3、Element Plus 和 MySQL 的软件项目实训项目，复用现有课程、学习、考试、用户和通知实现，分阶段完善校园教学业务。

## 当前阶段

**阶段 2：本地运行环境与数据库验证。** 已建立独立校园数据库、普通应用账号及启动入口。当前源码仍包含尚未适配的企业模块和历史问题，校园业务角色在阶段 3 开始处理。

- 正式源码位于 `backend/`，后续开发不依赖本地参考目录。
- `nov_lms/` 是本地复用参考项目，已整体忽略，不提交到 GitHub。
- 仅提取业务源码、静态页面和数据库迁移，不复制原配置、数据库、上传文件、虚拟环境或历史报告。
- 使用本机 Python 3.12.14 和已安装的 MySQL 8.4.11，不下载或重装运行环境。
- 使用项目内 `.runtime/mysql/` 数据目录与 `127.0.0.1:3309` 独立实例；启动、停止和初始化无需 Windows 管理员权限，不使用系统服务。

## 文档

- [需求说明书](docs/CAMPUS-LEARNING-REQUIREMENTS.md)：八个基本模块、45 条细分需求、14 个验收场景。
- [分阶段开发记录](docs/DEVELOPMENT.md)：各阶段范围、验证结果和下一步。

## 技术目标

| 部分 | 选择 |
|---|---|
| Python | 本机 3.12，本轮解释器为 3.12.14，不额外升级 Python |
| 后端 | FastAPI、Uvicorn、SQLAlchemy 同步模式、PyMySQL、Alembic |
| 数据库 | 本机已有 MySQL 8.4 LTS，独立校园库，不下载或重装数据库 |
| 前端 | 复用 Vue 3 + Element Plus + JavaScript 静态页面 |
| 文件 | 本地目录；资料鉴权在后续业务阶段完善 |

依赖清单为 `backend/requirements.txt`，可复现安装使用 `backend/requirements.lock.txt`（Windows x64 / Python 3.12）。已去掉本期不需要的 OSS SDK 和 Uvicorn 可选组件，显式保留 MySQL 默认认证需要的 RSA/加密依赖。

本轮已在干净虚拟环境从 wheel 独立安装锁定依赖，通过依赖一致性、5 项基础测试和真实数据库/HTTP 检查；完整在线下载遇到网络超时，安装验证使用了本机 wheel 缓存。

## 配置和运行方式

在普通 PowerShell 窗口、从仓库根目录执行。电脑需已有 Python 3.12 和 MySQL 8.4；脚本不会下载安装它们。默认 MySQL 程序位置为 `C:\Program Files\MySQL\MySQL Server 8.4\bin`。

```powershell
# 使用本机 Python 3.12 创建独立环境。
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock.txt
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-local.ps1
```

第一次运行会初始化项目数据目录、创建 `campus_learning` 数据库、仅授权该库的普通账号 `campus_app`、生成 `backend/.env` 和随机密钥、执行迁移，并创建平台管理员 `campus_admin`。登录密码保存在本地 `.runtime/admin.json`，可以在编辑器中查看；该文件不提交 Git。重复运行保留配置、密码和数据。

这里的平台管理员是应用业务角色，不是 Windows 管理员。MySQL 内部初始化账号只用于本项目实例的建库、授权和关闭，应用始终使用普通数据库账号 `campus_app`。

已有 `backend/.env` 若指向其他数据库，脚本会拒绝迁移并保留原文件。端口被其他项目占用也会拒绝复用。自定义已有 MySQL 安装位置可先执行：

```powershell
.\.venv\Scripts\python.exe scripts/setup_local.py --mysql-bin 'D:\MySQL\8.4\bin'
```

后续启动脚本会在数据库运行时复用它；若自定义安装路径且数据库已停止，先再次执行上述命令，再启动应用。

校园版入口：<http://127.0.0.1:20081/>。存活检查 `/api/v1/health` 不依赖数据库；就绪检查 `/api/v1/ready` 在数据库可用且已迁移时返回 200，否则返回 503；API 文档为 `/docs`。

## 日常启停

```powershell
# 启动数据库和应用；重复启动会复用本项目进程。
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-local.ps1
# 只停止本项目应用。
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/stop-local.ps1
# 同时关闭本项目数据库，不停止其他项目或系统服务。
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/stop-local.ps1 -Database
```

后端代码修改后先停止再启动。应用日志在 `.runtime/app.log`、`.runtime/app.err`，数据库日志在 `.runtime/mysql/server.log`。`.runtime/`、`backend/.env`、上传目录均被 Git 忽略。

本期仍是本地开发基线；校园权限、成绩逻辑和文件访问等问题在对应阶段处理，完成目标环境验证前不作为已验收系统对外部署。

## 环境检查

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.lock.txt
# 基础测试从 backend 目录运行。
Set-Location backend
..\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_bootstrap.py" -v
Set-Location ..
# 应用启动后验证真实 MySQL 和 HTTP 登录。
.\.venv\Scripts\python.exe scripts/check_environment.py
```

基础单元测试不连接数据库。`check_environment.py` 仅在本地校园库创建一条随机标记的临时课程，提交后用新会话校验中文与 JSON 持久化，并清理该行；另检查普通账号不能访问系统用户表、HTTP 登录和就绪接口，结果保存在 `.runtime/environment-check.json`。这不替代完整校园业务验收。
