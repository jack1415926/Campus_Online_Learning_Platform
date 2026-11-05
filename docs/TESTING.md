# 校园在线学习平台验证说明

验证日期：2026-11-05。当前结构包含25张业务表和1张迁移版本表；字段及约束以 [数据库清单](DATABASE.md) 为准。

## 本次结果

| 范围 | 结果 |
|---|---|
| 基础测试 | 5项通过，覆盖首页、配置、就绪检查和文件访问边界 |
| 前端检查 | JavaScript语法检查通过；上传、章节编辑、登录恢复、校验提示和阅卷组件共6项检查通过 |
| 课程和权限 | 14组、113次真实HTTP请求通过 |
| 学习和作业 | 5组、80次真实HTTP请求通过 |
| 考试和阅卷 | 5组、76次真实HTTP请求通过 |
| 讨论和私信 | 5组、73次真实HTTP请求通过 |
| 证书 | 5组、77次真实HTTP请求通过 |
| 设置和本地资源 | 4组、19次真实HTTP请求通过 |
| 章节排序 | 15次真实HTTP请求通过 |
| 空白简答题 | 30次真实HTTP请求通过 |
| 环境检查 | MySQL普通账号权限、中文及JSON跨会话持久化、实际登录和就绪检查通过 |
| 数据库初始化 | 隔离MySQL空库升级、模型结构比对、回退和重新升级通过 |
| 数据保留 | 清理时逐表比较保留字段，原有业务值保持一致 |
| 备份恢复 | 当前26张物理表及23个备份文件在独立目标恢复并通过校验 |
| 实际页面 | 学生、教师和管理员首页及师生课程详情加载正常，浏览器未记录脚本错误 |
| 演示账号 | 五个本地账号均可登录；重复初始化保留账号和进度 |

课程至设置的六组业务脚本共执行438次真实HTTP请求。组件检查使用受控替身，不能替代真实浏览器验证；本次页面检查覆盖上述入口，没有重新手动操作历史报告中的每一个页面验收场景。

## 运行方式

先按 [README](../README.md) 安装开发依赖并启动应用。

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
Set-Location ..
.\.venv\Scripts\python.exe scripts/check_environment.py
node scripts/check_acceptance_fixes.cjs
node scripts/check_blank_short_answers.cjs
```

需要检查完整业务时，依次执行下列脚本。它们使用项目独立数据库，并创建随机测试账号、课程及文件，不应与同一测试账号的人工操作同时运行。

```powershell
.\.venv\Scripts\python.exe scripts/check_stage3.py
.\.venv\Scripts\python.exe scripts/check_stage4.py
.\.venv\Scripts\python.exe scripts/check_stage5.py
.\.venv\Scripts\python.exe scripts/check_stage6.py
.\.venv\Scripts\python.exe scripts/check_stage7.py
.\.venv\Scripts\python.exe scripts/check_stage7_maintenance.py
```

章节和简答题的定向检查分别为 `scripts/check_chapter_order.py`、`scripts/check_blank_short_answers.py`。结果、测试账号和页面截图存放在本地 `.runtime/`，不放入源码提交包。

`docs/reports/` 保留标有日期的校园平台历史验收及复验材料；它们描述当时的验证范围，本次结果以本文件为准。
