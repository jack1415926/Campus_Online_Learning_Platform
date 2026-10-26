# 校园在线学习平台

基于 FastAPI、Vue 3、Element Plus 和 MySQL 的软件项目实训项目，复用现有课程、学习、考试、用户和通知实现，分阶段完善校园教学业务。

## 当前阶段

**阶段 1：独立源码基线与仓库初始化。** 当前源码仍包含尚未适配的企业模块和历史问题，不代表校园版八个模块已实现或验收通过。

- 正式源码位于 `backend/`，后续开发不依赖本地参考目录。
- `nov_lms/` 是本地复用参考项目，已整体忽略，不提交到 GitHub。
- 仅提取业务源码、静态页面和数据库迁移，不复制原配置、数据库、上传文件、虚拟环境或历史报告。
- 使用本机 Python 3.12 创建独立虚拟环境；MySQL 8.4 也复用本机现有安装，不下载、不重装，下一阶段只准备独立校园库并验证迁移。

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

`backend/requirements.txt` 为提取后的依赖基线，已移除本期不使用的 OSS SDK。阶段 1 已在本机 Python 3.12.14 独立环境通过 4 项基础检查；本轮复用了本机已安装依赖，不代表干净环境联网安装已验证。数据库和完整业务兼容性在后续阶段验证。

## 配置和运行方式

从仓库根目录执行；先自行准备独立 MySQL 库，使用只访问该库的应用账号。

```powershell
# 使用本机 Python 3.12 创建独立环境。
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
# 编辑 backend/.env，填入实际 DATABASE_URL 和随机 SECRET_KEY。
# 可用以下命令生成密钥：
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
Set-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 20081
```

校园版使用 `20081`，避免与原项目 `20080` 冲突。打开 `http://127.0.0.1:20081/`，健康接口为 `/api/v1/health`，API 文档为 `/docs`。阶段 1 尚未创建校园角色、管理员或演示数据，不能直接使用原项目账号登录。

本期仍是本地开发基线；校园权限、成绩逻辑和文件访问等问题在对应阶段处理，完成目标环境验证前不作为已验收系统对外部署。

## 阶段 1 检查

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
..\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_bootstrap.py" -v
```

上述检查不连接数据库，验证新项目配置、健康接口、页面入口和未知 API 的处理。不能替代真实 MySQL 8.4 迁移、学习、考试或权限验收。
