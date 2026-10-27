# 校园在线学习平台

基于 FastAPI、Vue 3、Element Plus 和 MySQL 的软件项目实训项目，复用现有课程、学习、考试、用户和通知实现，分阶段完善校园教学业务。

## 当前阶段

**阶段 5 已完成：手动组卷、四题型、固定满分、服务器截止、人工阅卷与成绩持久化。** 已通过针对性的真实 MySQL/HTTP 与页面验证。互动、证书等按后续阶段开发。

- 正式源码位于 `backend/`，后续开发不依赖本地参考目录。
- `nov_lms/` 是本地复用参考项目，已整体忽略，不提交到 GitHub。
- 仅提取业务源码、静态页面和数据库迁移，不复制原配置、数据库、上传文件、虚拟环境或历史报告。
- 使用 Python 3.12 和 MySQL 8.4；阶段 2 公司环境为 3.12.14 / 8.4.11，本次本机验证为 3.12.4 / 8.4.13。MySQL 可使用项目内便携版，无需管理员权限或系统服务。
- 使用项目内 `.runtime/mysql/` 数据目录与 `127.0.0.1:3309` 独立实例；启动、停止和初始化无需 Windows 管理员权限，不使用系统服务。

## 文档

- [需求说明书](docs/CAMPUS-LEARNING-REQUIREMENTS.md)：八个基本模块、45 条细分需求、14 个验收场景。
- [分阶段开发记录](docs/DEVELOPMENT.md)：各阶段范围、验证结果和下一步。

## 技术目标

| 部分 | 选择 |
|---|---|
| Python | 3.12；本次验证解释器为 3.12.4 |
| 后端 | FastAPI、Uvicorn、SQLAlchemy 同步模式、PyMySQL、Alembic |
| 数据库 | MySQL 8.4 LTS，独立校园库；支持已有安装或便携版 |
| 前端 | 复用 Vue 3 + Element Plus + JavaScript 静态页面 |
| 文件 | 本地目录；课程资料通过鉴权接口及短期资源链接访问 |

依赖清单为 `backend/requirements.txt`，可复现安装使用 `backend/requirements.lock.txt`（Windows x64 / Python 3.12）。已去掉本期不需要的 OSS SDK 和 Uvicorn 可选组件，显式保留 MySQL 默认认证需要的 RSA/加密依赖。

阶段 2 已完成干净环境 wheel 安装验证；本次在新的 `.venv` 中通过代理在线安装全部 36 项开发依赖，依赖一致性与 5 项基础测试通过。第三阶段回归为 14 组、113 次真实 HTTP 请求，结果范围见开发记录。

## 配置和运行方式

在普通 PowerShell 窗口、从仓库根目录执行。电脑需已有 Python 3.12 和 MySQL 8.4；脚本不会下载安装它们。默认 MySQL 程序位置为 `C:\Program Files\MySQL\MySQL Server 8.4\bin`。

```powershell
# 使用本机 Python 3.12 创建独立环境。
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock.txt
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-local.ps1
```

第一次运行会初始化项目数据目录、创建 `campus_learning` 数据库、仅授权该库的普通账号 `campus_app`、生成 `backend/.env` 和随机密钥、执行迁移，并创建平台管理员 `campus_admin`。登录密码保存在本地 `.runtime/admin.json`，可以在编辑器中查看；该文件不提交 Git。重复运行保留配置、密码和数据。学生可直接注册；教师注册后需平台管理员审核，通过后才显示建课入口。

这里的平台管理员是应用业务角色，不是 Windows 管理员。MySQL 内部初始化账号只用于本项目实例的建库、授权和关闭，应用始终使用普通数据库账号 `campus_app`。

已有 `backend/.env` 若指向其他数据库，脚本会拒绝迁移并保留原文件。端口被其他项目占用也会拒绝复用。自定义已有 MySQL 安装位置可先执行：

```powershell
.\.venv\Scripts\python.exe scripts/setup_local.py --mysql-bin 'D:\MySQL\8.4\bin'
```

脚本会在本地忽略的凭据文件中记住成功使用的 MySQL 程序路径。后续直接使用 `start-local.ps1`，数据库停止后也能从该路径启动；命令行 `--mysql-bin` 可覆盖旧路径。

公司电脑没有 Windows 管理员权限时，同样在普通终端运行。如果没有已有 MySQL 8.4 安装，可从 [MySQL 官方 Windows 下载页](https://dev.mysql.com/downloads/mysql/8.4.html?os=3) 获取 ZIP 便携版，核对官方校验值后解压到项目 `.local/`（不提交 Git）。例如本次使用：

```powershell
.\.venv\Scripts\python.exe scripts/setup_local.py --mysql-bin '.local/mysql-8.4.13-winx64/bin'
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-local.ps1
```

不需要以管理员身份打开终端，不使用 `RunAs` 或 UAC，不安装/控制 Windows 服务，也不使用系统 MySQL 数据目录。MySQL 自带的内部初始化账号只用于本项目实例的建库、授权和关闭，不创建额外的 MySQL 管理员账号；应用和迁移使用普通账号 `campus_app`。网页 `campus_admin` 只是教师和课程审核所需的业务角色。若公司策略禁止运行便携程序，应按该策略处理；本次没有实际在公司电脑复测。

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

当前完成阶段 1～5。教师在题库管理维护本人四题型，在本人草稿课程内准备作业及手动试卷，随课程审核发布开放；学生在课程内提交作业、考试、查看结果，教师使用共用表格/弹窗批改。未批与 0 分分别展示，简答题全部批完才生成最终考试结论。随机组卷、刷题、错题本、Excel 导入与分析看板入口不开放，既有辅助接口限管理员。本阶段通过不代表全部需求已验收或可对外部署。

## 环境检查

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.lock.txt
# 基础测试从 backend 目录运行。
Set-Location backend
..\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_bootstrap.py" -v
Set-Location ..
# 应用启动后验证真实 MySQL 和 HTTP 登录。
.\.venv\Scripts\python.exe scripts/check_environment.py
# 第三阶段真实接口回归（会创建随机测试账号、课程和文件，不清空现有数据）。
.\.venv\Scripts\python.exe scripts/check_stage3.py
# 阶段四回归，复用上一步生成的本地随机测试账号。
.\.venv\Scripts\python.exe scripts/check_stage4.py
# 阶段五核心回归；已有测试账号时可直接运行，无需重跑前两项。
.\.venv\Scripts\python.exe scripts/check_stage5.py
# 只补查提前关闭、过期列表和归档边界。
.\.venv\Scripts\python.exe scripts/check_stage5.py --edges
```

基础单元测试不连接数据库。`check_environment.py` 仅在本地校园库创建一条随机标记的临时课程，提交后用新会话校验中文与 JSON 持久化，并清理该行；另检查普通账号不能访问系统用户表、HTTP 登录和就绪接口，结果保存在 `.runtime/environment-check.json`。这不替代完整校园业务验收。

`check_stage3.py` 的摘要和测试凭据分别保存在 `.runtime/stage3-results.json`、`.runtime/stage3-accounts.json`；不要公开凭据文件。测试数据保留用于本地页面回归；脚本会重新登录测试管理员，请勿同时用该账号进行其他验证（系统采用单会话登录）。页面验收截图位于 `.runtime/stage3-browser/`，不提交 Git。

`check_stage4.py` 覆盖两章进度、完成通知去重、续播位置、作业提交/修改/批改、附件权限、截止与归档限制，结果在 `.runtime/stage4-results.json`。本次为 5 组、80 次真实请求通过，页面证据在 `.runtime/stage4-browser/`。视频和 PDF 样例仅用于本机验证，不提交 Git。阶段四迁移会为学习记录增加唯一约束；如旧库已有同一学生/章节的重复行，会明确停止并要求检查历史数据，不自动删除记录。

阶段五结果在 `.runtime/stage5-results.json`（5 组、76 次请求）和 `.runtime/stage5-edge-results.json`（3 项边界、18 次请求），页面证据在 `.runtime/stage5-browser/`。上述检查按改动范围选用，不要求每次全部执行。学生刷新会恢复原尝试、已保存答案和服务器截止；超过截止的新答案不计入，按此前保存的答案结束尝试。旧答卷若无试卷快照，不以当前题库重新计算历史分数；迁移发现重复尝试号会停止并要求复核，不自动删除记录。
