"""从 SQLAlchemy 模型反射生成数据库清单文档。

用法（在 backend 目录或仓库根目录均可）：
    .venv\\Scripts\\python.exe scripts\\db_inventory.py

输出：
    docs/DATABASE.md            表清单 / 字段 / 唯一约束 / 关系（Git 跟踪）
    docs/数据库表清单.xlsx      同上，可筛选（二进制，可选提交）
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import UniqueConstraint  # noqa: E402
from app.models import Base  # noqa: E402

OUT = ROOT / "docs"

# 表 -> (业务分组, 中文含义)
META = {
    "users": ("① 登录与权限", "用户（学生/教师/管理员）"),
    "sessions": ("① 登录与权限", "登录会话"),
    "roles": ("① 登录与权限", "角色"),
    "permissions": ("① 登录与权限", "权限点"),
    "user_roles": ("① 登录与权限", "用户-角色（含数据范围）"),
    "role_permissions": ("① 登录与权限", "角色-权限"),
    "organizations": ("① 登录与权限", "部门（自引用树）"),
    "courses": ("② 课程与资料", "课程"),
    "chapters": ("② 课程与资料", "章节"),
    "media_assets": ("② 课程与资料", "素材库（视频/文档/图片）"),
    "media_categories": ("② 课程与资料", "素材分类"),
    "categories": ("② 课程与资料", "课程分类"),
    "tags": ("② 课程与资料", "标签"),
    "course_tags": ("② 课程与资料", "课程-标签"),
    "course_assignments": ("③ 学习与作业", "选课 / 课程分配"),
    "learning_records": ("③ 学习与作业", "学习进度"),
    "homeworks": ("③ 学习与作业", "作业"),
    "homework_submissions": ("③ 学习与作业", "作业提交"),
    "training_plans": ("③ 学习与作业", "培训计划"),
    "learning_paths": ("③ 学习与作业", "学习路径"),
    "plan_courses": ("③ 学习与作业", "计划-课程"),
    "path_courses": ("③ 学习与作业", "路径-课程"),
    "exams": ("④ 考试", "考试"),
    "exam_records": ("④ 考试", "考试答卷"),
    "questions": ("④ 考试", "题目"),
    "question_banks": ("④ 考试", "题库"),
    "discussion_topics": ("⑤ 交流与通知", "讨论主题"),
    "discussion_replies": ("⑤ 交流与通知", "讨论回复"),
    "private_messages": ("⑤ 交流与通知", "私信"),
    "notifications": ("⑤ 交流与通知", "站内通知"),
    "notification_templates": ("⑤ 交流与通知", "通知模板"),
    "certificates": ("⑥ 结果与平台", "结课证书"),
    "platform_settings": ("⑥ 结果与平台", "平台设置"),
    "job_levels": ("⑦ 组织字典", "职级字典"),
    "positions": ("⑦ 组织字典", "岗位字典"),
}

DUP = {
    "uq_learning_user_chapter": "同一学生对同一章只保留一条进度。注意 chapter_id 可空，MySQL 唯一索引不约束 NULL 行，实际由课程行锁兜底",
    "uq_exam_attempt": "同一学生同一考试的同一尝试号只有一条",
    "uq_homework_student": "同一作业同一学生只有一份提交",
    "uq_certificate_student_course": "同一课程同一学生只能领一张证书",
    "uq_course_assignment_target": "同一课程同一分配类型同一目标只能分配一次",
    "uq_notification_event": "同一事件只发一条通知（防重复提醒）",
}


def usage_of(class_name: str, table_name: str) -> list[str]:
    """定位模型被哪些接口/服务模块实际引用。

    只按“属性访问 / 查询构造 / 实例化”判断，避免 Session、Course 这类通用词
    被类型注解误匹配成整库都在用。关联表没有映射类，退回按变量名匹配。
    """
    ident = class_name or table_name
    if class_name:
        patterns = [
            re.compile(rf"\b{ident}\."),
            re.compile(rf"(?:select|get|insert|delete|update)\(\s*{ident}\b"),
            re.compile(rf"\b{ident}\("),
        ]
    else:
        patterns = [re.compile(rf"\b{ident}\b")]
    hits = []
    for folder in ("api/v1", "services", "core"):
        for path in (ROOT / "backend" / "app" / folder).glob("*.py"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(p.search(text) for p in patterns):
                hits.append(f"{folder}/{path.name}")
    return sorted(hits)


mappers = {m.class_.__tablename__: m.class_.__name__ for m in Base.registry.mappers}
tables = list(Base.metadata.sorted_tables)

rows = []
for table in tables:
    cols = list(table.columns)
    fks = [c for c in cols if c.foreign_keys]
    uniques = [c for c in table.constraints if isinstance(c, UniqueConstraint)]
    group, cn = META.get(table.name, ("⑨ 未分类", ""))
    rows.append(
        {
            "name": table.name,
            "group": group,
            "cn": cn,
            "cols": len(cols),
            "fks": len(fks),
            "uniques": len(uniques),
            "indexes": len(table.indexes),
            "usage": usage_of(mappers.get(table.name, ""), table.name),
            "table": table,
        }
    )

total_cols = sum(r["cols"] for r in rows)
total_fk = sum(r["fks"] for r in rows)
unique_con_names = [
    c.name for t in tables for c in t.constraints
    if isinstance(c, UniqueConstraint) and c.name
]
unique_cols = [f"{t.name}.{c.name}" for t in tables for c in t.columns if c.unique]
loose = [
    (t.name, c.name)
    for t in tables
    for c in t.columns
    if not c.foreign_keys and not c.primary_key and (c.name.endswith("_id") or c.name.endswith("_by"))
]

lines = [
    "# 数据库表清单（当前实际状态）",
    "",
    "> 本文件由 `scripts/db_inventory.py` 从 SQLAlchemy 模型反射生成，请勿手工编辑；",
    "> 改表后重新运行：`.venv\\Scripts\\python.exe scripts\\db_inventory.py`。",
    "",
    "## 总计",
    "",
    "| 项目 | 数量 |",
    "|---|---:|",
    f"| 业务表（models 声明） | **{len(tables)}** |",
    f"| 物理表（含 `alembic_version`） | **{len(tables) + 1}** |",
    f"| 字段总数 | **{total_cols}** |",
    f"| 外键（按模型统计） | **{total_fk}** |",
    f"| 逻辑关联（无外键约束） | **{len(loose)}** |",
    f"| 组合唯一约束 | **{len(unique_con_names)}** |",
    f"| 单列唯一 | **{len(unique_cols)}** |",
    "",
    "`docs/DEVELOPMENT.md` 中“29 张表”是阶段 2、阶段 3 当时的历史记录"
    "（28 张业务表 + 迁移表）。此后阶段 4～7 陆续新增作业、交流、证书、设置等表，",
    f"2026-11-02 移除 8 张旧企业功能表后，当前为 {len(tables)} 张业务表。历史记录不改写。",
    "",
    "## 表清单",
    "",
    "| # | 分组 | 表名 | 含义 | 字段 | 外键 | 唯一 | 被谁使用 |",
    "|---:|---|---|---|---:|---:|---:|---|",
]
for i, r in enumerate(rows, 1):
    usage = "<br>".join(f"`{u}`" for u in r["usage"]) or "—"
    lines.append(
        f"| {i} | {r['group']} | `{r['name']}` | {r['cn']} | {r['cols']} | {r['fks']} | "
        f"{r['uniques']} | {usage} |"
    )

lines += ["", "## 组合唯一约束", "", "| 表 | 约束名 | 字段 | 防的是什么 |", "|---|---|---|---|"]
for table in tables:
    for con in table.constraints:
        if isinstance(con, UniqueConstraint) and con.name:
            lines.append(
                f"| `{table.name}` | `{con.name or ''}` | "
                f"{', '.join(c.name for c in con.columns)} | {DUP.get(con.name, '')} |"
            )

lines += ["", "## 单列唯一", "", "| 表.字段 |", "|---|"]
lines += [f"| `{u}` |" for u in unique_cols]

lines += [
    "",
    "## 物理外键（数据库强制）",
    "",
    "| 子表 | 字段 | → 父表.字段 | 删除行为 |",
    "|---|---|---|---|",
]
for table in tables:
    for col in table.columns:
        for fk in col.foreign_keys:
            lines.append(
                f"| `{table.name}` | `{col.name}` | `{fk.target_fullname}` | "
                f"{fk.ondelete or 'NO ACTION'} |"
            )

lines += [
    "",
    "## 逻辑关联（数据库不强制，由服务层校验）",
    "",
    "| 表 | 字段 | 说明 |",
    "|---|---|---|",
]
for table_name, col_name in loose:
    lines.append(f"| `{table_name}` | `{col_name}` | 无外键约束 |")

(OUT / "DATABASE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

# 可选：同时输出可筛选的表格
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "表清单"
    ws.append(["序号", "分组", "表名", "含义", "字段数", "外键数", "唯一约束数", "使用位置"])
    for i, r in enumerate(rows, 1):
        ws.append([i, r["group"], r["name"], r["cn"], r["cols"], r["fks"], r["uniques"], ", ".join(r["usage"])])
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for idx, width in enumerate([6, 16, 26, 26, 8, 8, 10, 60], 1):
        ws.column_dimensions[chr(64 + idx)].width = width
    ws.freeze_panes = "A2"

    ws2 = wb.create_sheet("字段清单")
    ws2.append(["表名", "字段名", "类型", "可空", "主键", "外键指向", "唯一", "有索引"])
    for table in tables:
        for col in table.columns:
            ws2.append([
                table.name,
                col.name,
                str(col.type),
                "是" if col.nullable else "否",
                "是" if col.primary_key else "",
                ", ".join(str(fk.target_fullname) for fk in col.foreign_keys),
                "是" if col.unique else "",
                "是" if col.index else "",
            ])
    for idx, width in enumerate([22, 24, 34, 6, 6, 30, 6, 8], 1):
        ws2.column_dimensions[chr(64 + idx)].width = width
    ws2.freeze_panes = "A2"

    wb.save(OUT / "数据库表清单.xlsx")
    xlsx_note = " + 数据库表清单.xlsx"
except ImportError:
    xlsx_note = ""

print(
    f"tables={len(tables)} columns={total_cols} fk={total_fk} "
    f"unique={len(unique_con_names)}+{len(unique_cols)} loose={len(loose)}"
)
print(f"-> docs/DATABASE.md{xlsx_note}")
