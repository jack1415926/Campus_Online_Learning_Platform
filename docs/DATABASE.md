# 数据库表清单（当前实际状态）

> 本文件由 `scripts/db_inventory.py` 从 SQLAlchemy 模型反射生成，请勿手工编辑；
> 改表后重新运行：`.venv\Scripts\python.exe scripts\db_inventory.py`。

## 总计

| 项目 | 数量 |
|---|---:|
| 业务表（models 声明） | **27** |
| 物理表（含 `alembic_version`） | **28** |
| 字段总数 | **272** |
| 外键（按模型统计） | **24** |
| 逻辑关联（无外键约束） | **26** |
| 组合唯一约束 | **6** |
| 单列唯一 | **8** |

`docs/DEVELOPMENT.md` 中“29 张表”是阶段 2、阶段 3 当时的历史记录（28 张业务表 + 迁移表）。此后阶段 4～7 陆续新增作业、交流、证书、设置等表，
2026-11-02 移除 8 张旧企业功能表后，当前为 27 张业务表。历史记录不改写。

## 表清单

| # | 分组 | 表名 | 含义 | 字段 | 外键 | 唯一 | 被谁使用 |
|---:|---|---|---|---:|---:|---:|---|
| 1 | ② 课程与资料 | `categories` | 课程分类 | 8 | 1 | 0 | `api/v1/categories.py`<br>`services/category_service.py` |
| 2 | ④ 考试 | `exam_records` | 考试答卷 | 21 | 0 | 1 | `api/v1/certificates.py`<br>`api/v1/exams.py`<br>`api/v1/learning.py`<br>`services/campus_exam_service.py`<br>`services/exam_service.py`<br>`services/learning_service.py` |
| 3 | ④ 考试 | `exams` | 考试 | 20 | 0 | 0 | `api/v1/courses.py`<br>`api/v1/exams.py`<br>`api/v1/learning.py`<br>`services/campus_exam_service.py`<br>`services/course_service.py`<br>`services/exam_service.py`<br>`services/learning_service.py` |
| 4 | ② 课程与资料 | `media_assets` | 素材库（视频/文档/图片） | 15 | 0 | 0 | `api/v1/courses.py`<br>`api/v1/media.py`<br>`services/media_service.py` |
| 5 | ② 课程与资料 | `media_categories` | 素材分类 | 6 | 0 | 0 | `services/media_service.py` |
| 6 | ⑤ 交流与通知 | `notifications` | 站内通知 | 13 | 0 | 1 | `api/v1/communication.py`<br>`services/campus_exam_service.py`<br>`services/deadline_reminder_service.py`<br>`services/learning_service.py`<br>`services/notification_service.py` |
| 7 | ① 登录与权限 | `permissions` | 权限点 | 7 | 0 | 0 | `core/rbac.py`<br>`core/seed.py` |
| 8 | ⑥ 结果与平台 | `platform_settings` | 平台设置 | 3 | 0 | 0 | `api/v1/auth.py`<br>`api/v1/certificates.py`<br>`api/v1/platform.py` |
| 9 | ④ 考试 | `question_banks` | 题库 | 6 | 0 | 0 | `services/campus_exam_service.py`<br>`services/exam_service.py` |
| 10 | ④ 考试 | `questions` | 题目 | 14 | 0 | 0 | `api/v1/exams.py`<br>`services/campus_exam_service.py`<br>`services/exam_service.py` |
| 11 | ① 登录与权限 | `roles` | 角色 | 7 | 0 | 0 | `api/v1/auth.py`<br>`api/v1/communication.py`<br>`api/v1/users.py`<br>`core/campus_access.py`<br>`core/rbac.py`<br>`core/seed.py`<br>`services/learning_service.py` |
| 12 | ① 登录与权限 | `sessions` | 登录会话 | 9 | 0 | 0 | `services/session_service.py` |
| 13 | ② 课程与资料 | `tags` | 标签 | 4 | 0 | 0 | `api/v1/categories.py`<br>`services/category_service.py`<br>`services/course_service.py` |
| 14 | ① 登录与权限 | `users` | 用户（学生/教师/管理员） | 20 | 0 | 0 | `api/v1/auth.py`<br>`api/v1/communication.py`<br>`api/v1/homework.py`<br>`api/v1/learning.py`<br>`api/v1/media.py`<br>`api/v1/users.py`<br>`core/seed.py`<br>`services/learning_service.py`<br>`services/user_service.py` |
| 15 | ② 课程与资料 | `courses` | 课程 | 19 | 1 | 0 | `api/v1/certificates.py`<br>`api/v1/communication.py`<br>`api/v1/courses.py`<br>`api/v1/exams.py`<br>`api/v1/homework.py`<br>`api/v1/learning.py`<br>`api/v1/media.py`<br>`core/campus_access.py`<br>`services/campus_exam_service.py`<br>`services/course_service.py`<br>`services/deadline_reminder_service.py`<br>`services/learning_service.py` |
| 16 | ① 登录与权限 | `role_permissions` | 角色-权限 | 2 | 2 | 0 | `core/rbac.py` |
| 17 | ① 登录与权限 | `user_roles` | 用户-角色（含数据范围） | 6 | 2 | 0 | `api/v1/auth.py`<br>`api/v1/communication.py`<br>`api/v1/users.py`<br>`core/campus_access.py`<br>`core/rbac.py`<br>`core/seed.py`<br>`services/learning_service.py` |
| 18 | ⑥ 结果与平台 | `certificates` | 结课证书 | 9 | 3 | 2 | `api/v1/certificates.py`<br>`api/v1/courses.py`<br>`api/v1/learning.py` |
| 19 | ② 课程与资料 | `chapters` | 章节 | 12 | 1 | 0 | `api/v1/courses.py`<br>`api/v1/learning.py`<br>`api/v1/media.py`<br>`core/campus_access.py`<br>`services/course_service.py`<br>`services/learning_service.py` |
| 20 | ③ 学习与作业 | `course_assignments` | 选课 / 课程分配 | 9 | 1 | 1 | `api/v1/communication.py`<br>`api/v1/courses.py`<br>`api/v1/learning.py`<br>`core/campus_access.py`<br>`services/deadline_reminder_service.py`<br>`services/learning_service.py` |
| 21 | ② 课程与资料 | `course_tags` | 课程-标签 | 2 | 2 | 0 | — |
| 22 | ⑤ 交流与通知 | `discussion_topics` | 讨论主题 | 8 | 2 | 0 | `api/v1/communication.py` |
| 23 | ③ 学习与作业 | `homeworks` | 作业 | 10 | 1 | 0 | `api/v1/certificates.py`<br>`api/v1/courses.py`<br>`api/v1/homework.py`<br>`api/v1/learning.py` |
| 24 | ③ 学习与作业 | `learning_records` | 学习进度 | 14 | 1 | 1 | `services/deadline_reminder_service.py`<br>`services/learning_service.py` |
| 25 | ⑤ 交流与通知 | `private_messages` | 私信 | 7 | 3 | 0 | `api/v1/communication.py` |
| 26 | ⑤ 交流与通知 | `discussion_replies` | 讨论回复 | 7 | 2 | 0 | `api/v1/communication.py` |
| 27 | ③ 学习与作业 | `homework_submissions` | 作业提交 | 14 | 2 | 1 | `api/v1/certificates.py`<br>`api/v1/courses.py`<br>`api/v1/homework.py`<br>`api/v1/learning.py` |

## 组合唯一约束

| 表 | 约束名 | 字段 | 防的是什么 |
|---|---|---|---|
| `exam_records` | `uq_exam_attempt` | exam_id, user_id, attempt_number | 同一学生同一考试的同一尝试号只有一条 |
| `notifications` | `uq_notification_event` | event_key | 同一事件只发一条通知（防重复提醒） |
| `certificates` | `uq_certificate_student_course` | course_id, user_id | 同一课程同一学生只能领一张证书 |
| `course_assignments` | `uq_course_assignment_target` | course_id, assignment_type, target_id | 同一课程同一分配类型同一目标只能分配一次 |
| `learning_records` | `uq_learning_user_chapter` | user_id, course_id, chapter_id | 同一学生对同一章只保留一条进度。注意 chapter_id 可空，MySQL 唯一索引不约束 NULL 行，实际由课程行锁兜底 |
| `homework_submissions` | `uq_homework_student` | homework_id, user_id | 同一作业同一学生只有一份提交 |

## 单列唯一

| 表.字段 |
|---|
| `permissions.code` |
| `roles.code` |
| `sessions.token` |
| `tags.name` |
| `users.username` |
| `users.email` |
| `users.employee_id` |
| `certificates.number` |

## 物理外键（数据库强制）

| 子表 | 字段 | → 父表.字段 | 删除行为 |
|---|---|---|---|
| `categories` | `parent_id` | `categories.id` | NO ACTION |
| `courses` | `category_id` | `categories.id` | NO ACTION |
| `role_permissions` | `role_id` | `roles.id` | CASCADE |
| `role_permissions` | `permission_id` | `permissions.id` | CASCADE |
| `user_roles` | `user_id` | `users.id` | CASCADE |
| `user_roles` | `role_id` | `roles.id` | CASCADE |
| `certificates` | `course_id` | `courses.id` | NO ACTION |
| `certificates` | `user_id` | `users.id` | NO ACTION |
| `certificates` | `exam_record_id` | `exam_records.id` | NO ACTION |
| `chapters` | `course_id` | `courses.id` | CASCADE |
| `course_assignments` | `course_id` | `courses.id` | CASCADE |
| `course_tags` | `course_id` | `courses.id` | CASCADE |
| `course_tags` | `tag_id` | `tags.id` | CASCADE |
| `discussion_topics` | `course_id` | `courses.id` | NO ACTION |
| `discussion_topics` | `user_id` | `users.id` | NO ACTION |
| `homeworks` | `course_id` | `courses.id` | CASCADE |
| `learning_records` | `course_id` | `courses.id` | CASCADE |
| `private_messages` | `course_id` | `courses.id` | NO ACTION |
| `private_messages` | `sender_id` | `users.id` | NO ACTION |
| `private_messages` | `recipient_id` | `users.id` | NO ACTION |
| `discussion_replies` | `topic_id` | `discussion_topics.id` | NO ACTION |
| `discussion_replies` | `user_id` | `users.id` | NO ACTION |
| `homework_submissions` | `homework_id` | `homeworks.id` | CASCADE |
| `homework_submissions` | `user_id` | `users.id` | NO ACTION |

## 逻辑关联（数据库不强制，由服务层校验）

| 表 | 字段 | 说明 |
|---|---|---|
| `exam_records` | `user_id` | 无外键约束 |
| `exam_records` | `exam_id` | 无外键约束 |
| `exam_records` | `graded_by` | 无外键约束 |
| `exams` | `course_id` | 无外键约束 |
| `exams` | `created_by` | 无外键约束 |
| `media_assets` | `category_id` | 无外键约束 |
| `media_assets` | `uploaded_by` | 无外键约束 |
| `media_categories` | `created_by` | 无外键约束 |
| `notifications` | `user_id` | 无外键约束 |
| `question_banks` | `created_by` | 无外键约束 |
| `questions` | `created_by` | 无外键约束 |
| `questions` | `question_bank_id` | 无外键约束 |
| `sessions` | `user_id` | 无外键约束 |
| `users` | `employee_id` | 无外键约束 |
| `users` | `teacher_reviewed_by` | 无外键约束 |
| `courses` | `certificate_exam_id` | 无外键约束 |
| `courses` | `created_by` | 无外键约束 |
| `courses` | `reviewed_by` | 无外键约束 |
| `chapters` | `content_ref_id` | 无外键约束 |
| `course_assignments` | `target_id` | 无外键约束 |
| `course_assignments` | `assigned_by` | 无外键约束 |
| `discussion_topics` | `deleted_by` | 无外键约束 |
| `learning_records` | `user_id` | 无外键约束 |
| `learning_records` | `chapter_id` | 无外键约束 |
| `discussion_replies` | `deleted_by` | 无外键约束 |
| `homework_submissions` | `graded_by` | 无外键约束 |
