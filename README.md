# 校园在线学习平台

面向学生、教师和管理员，提供课程审核、章节学习、作业提交与批改、限时考试与阅卷、讨论私信、进度查看和结课证书。

## 技术与目录

使用 Python 3.12、FastAPI、SQLAlchemy、MySQL 8.4、Vue 3 和 Element Plus。前端为静态页面，无需单独构建；运行资源已放在本地。

| 目录 | 内容 |
|---|---|
| `backend/app/` | 接口、业务服务、模型及数据校验 |
| `backend/static/` | 页面、脚本及第三方前端资源 |
| `backend/alembic/` | 校园版数据库初始迁移 |
| `backend/tests/` | 基础测试 |
| `scripts/` | 启动、演示数据、检查和备份工具 |
| `docs/` | 需求、设计、报告和图示 |

## 安装与启动

在仓库根目录使用普通 PowerShell。需已有 Python 3.12 和 MySQL 8.4 安装或 ZIP 便携版，脚本不会安装系统服务。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock.txt
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-local.ps1
```

默认 MySQL 程序位置为 `C:\Program Files\MySQL\MySQL Server 8.4\bin`。使用其他位置时先执行下面的命令，程序路径会被记住：

```powershell
.\.venv\Scripts\python.exe scripts/setup_local.py --mysql-bin 'D:\MySQL\8.4\bin'
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-local.ps1
```

数据库仅监听 `127.0.0.1:3309`，使用项目独立数据目录及 `campus_learning` 数据库。脚本生成 `backend/.env`，执行迁移并创建管理员，应用使用普通数据库账号 `campus_app`。

访问 [本地平台](http://127.0.0.1:20081/)。初始管理员为 **`admin` / `123456`**，用于本地测试。账号文件在 `.runtime/admin.json`；重复启动保留账号和业务数据。

接口文档为 `/docs`，存活检查为 `/api/v1/health`，数据库就绪检查为 `/api/v1/ready`。

```powershell
# 停止应用。
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/stop-local.ps1
# 同时停止项目数据库。
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/stop-local.ps1 -Database
```

应用日志在 `.runtime/app.log`、`.runtime/app.err`，数据库日志在 `.runtime/mysql/server.log`。修改后端代码后需重启应用。

## 演示

```powershell
.\.venv\Scripts\python.exe scripts/setup_demo.py
```

演示管理员 `admin2`、教师 `teacher`、学生 `stu1` 和 `stu2` 的初始密码均为 `123456`。脚本准备两章课程、作业、五题考试、讨论和证书规则；重复执行保留已有进度。作业与考试在首次初始化后30天内开放。

具体顺序见 [演示操作说明](docs/DEMO.md)。同一账号再次登录会使原会话失效，请用不同账号演示不同角色。

## 检查

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.lock.txt
Set-Location backend
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
Set-Location ..
.\.venv\Scripts\python.exe scripts/check_environment.py
```

基础测试不连接数据库。真实业务检查会创建测试数据，具体范围见 [验证说明](docs/TESTING.md)。

## 备份和恢复

先停止应用并保持数据库运行，再执行备份；结果保存在 `backups/`，包含数据库、上传文件和校验清单。

```powershell
.\.venv\Scripts\python.exe scripts/backup_restore.py backup
```

恢复使用新的独立目标库，运行库继续使用原数据库：

```powershell
.\.venv\Scripts\python.exe scripts/backup_restore.py restore --backup 'backups/<备份目录>' --database campus_restore_demo --confirm-target campus_restore_demo
```

## 文档与源码提交

- [需求说明](docs/CAMPUS-LEARNING-REQUIREMENTS.md)
- [设计说明](docs/DESIGN.md)
- [数据库清单](docs/DATABASE.md)
- [图示使用说明](docs/报告图示使用说明.md)

源码提交包排除 `.git/`、`.venv/`、`.local/`、`.runtime/`、`backups/`、私有 `.env` 和 `backend/storage/`。第三方前端资源的许可证随源码保留。
