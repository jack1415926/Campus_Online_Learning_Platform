# 需求实现核查与空白简答题计分调整

日期：2026-10-30（Asia/Shanghai）。代码起点：`e460773`；需求基线：V1.4，附本日用户确认的空白简答题规则。

**后续处理：** 用户随后授权继续开发。以下为发现问题时的原始核查结论；CM-02 的两项缺口现已补齐，新增演示初始化及设计说明，验证见 [本轮完成记录](COMPLETION-2026-10-30.md)。正式实训报告和提交包经用户确认留待后续。

## 核查结论

**不能认定所有需求已完整实现。** 45 条功能需求中，44 条找到对应实现及既有验证记录；CM-02 仍为部分实现：教师页面缺少章节排序操作，编辑章节的素材刷新仍会误传点击事件。该结论是本次代码核查结合历史验收所得，不是本日重新完成 45 条实际页面验收。

既有[全流程验收](ACCEPTANCE-2026-10-29.md)记录 42 条通过、2 条不通过、1 条部分通过；[定向修复记录](FIXES-2026-10-30.md)补充 DOCX 上传、新增章节素材选择、失效会话及邮箱提示的复验。本次发现旧 CM-02 验收没有覆盖章节排序，素材刷新修复也遗漏了编辑弹窗，因此不能直接把两份报告相加称为“全部通过”。历史报告不改写。

## 逐条对应

“有实现”表示本次找到相应代码并结合既有验收记录核查；不表示本日逐条重测。代码位置均相对仓库根目录。

| 需求 | 核查结果 | 主要实现及核查内容 |
|---|---|---|
| UM-01 | 有实现 | `auth.py`、`auth/`、`schemas/auth.py`：注册、唯一性、登录与密码摘要 |
| UM-02 | 有实现 | `auth.py`、`users.py`、`campus_access.py`：教师待审、通过/驳回、权限控制 |
| UM-03 | 有实现 | `users.py`、`user_service.py`：搜索、角色分配、启停与审核 |
| UM-04 | 有实现 | `users.py`、`schemas/user.py`：本人资料、邮箱校验、原密码验证 |
| UM-05 | 有实现 | `auth.py`、`session_service.py`、`api/deps.py`、`api.js`：撤销与过期会话、页面恢复 |
| CM-01 | 有实现 | `courses.py`、`course_service.py`、`app.js`：课程信息、封面、按名称搜索、大纲 |
| CM-02 | **部分实现** | `courses.py` 支持章节增删改与 `sort_order`；`app.js` 无排序控件，编辑弹窗刷新传入事件对象 |
| CM-03 | 有实现 | `courses.py:publish_action`：有效章节、提交审核、驳回与发布 |
| CM-04 | 有实现 | `campus_access.py:get_course`、`courses.py:_ensure_no_activity`：冻结、退回与归档保护 |
| CM-05 | 有实现 | `media.py`、`homework.py`、`app.js`：格式、大小、文件头、随机文件路径；DOCX 上传有定向复验 |
| LM-01 | 有实现 | `courses.py:join_course`、`models/learning.py`：搜索、加入与成员唯一约束 |
| LM-02 | 有实现 | `campus_access.py`、`media.py`、`core/media_access.py`、`app.js`：成员访问、视频/PDF/DOCX |
| LM-03 | 有实现 | `learning_service.py`、`app.js`：播放位置、续播、章节完成 |
| LM-04 | 有实现 | `app.js` 课程内面板及各业务接口：作业/考试/讨论关联入口、归档历史 |
| AS-01 | 有实现 | `homework.py`、`schemas/homework.py`、`homework.js`：草稿内配置要求、截止、分值及必交 |
| AS-02 | 有实现 | `homework.py:submit_homework`：文字/单附件、当前提交唯一、截止前未批可改 |
| AS-03 | 有实现 | `homework.py:grade_submission`、`homework.js`：师生范围、分数评语及保存 |
| AS-04 | 有实现 | `homework.py`：截止与已批拒交、未批与零分区分、存在提交保护 |
| EX-01 | 有实现 | `schemas/exam.py`、`exams.py`、`app.js`：四题型、选项答案与题库归属 |
| EX-02 | 有实现 | `campus_exam_service.py:write_exam`、`exams.js`：手动组卷、课程、时段、时长、分值与次数 |
| EX-03 | 有实现 | `campus_exam_service.py:start/expire`、`app.js`：身份、次数、服务器截止与倒计时 |
| EX-04 | 有实现；本次修改 | `campus_exam_service.py:submit`：客观题自动判分，空白简答自动 0 分，非空人工阅卷 |
| EX-05 | 有实现 | `validate_answers/submit`：固定满分、漏答零分、重复/卷外拒绝、交卷幂等 |
| EX-06 | 有实现；本次修改 | `grade/finalize`、`exams.js`：空白题已批；非空题部分批改仍待批、最终结果冻结 |
| EX-07 | 有实现 | `exams.py`、`exams.js`：本人记录、教师列表与逐题详情 |
| EX-08 | 有实现 | `write_exam/start`、`models/exam.py`：试卷与答卷快照、历史满分及删除保护 |
| CO-01 | 有实现 | `communication.py`、`communication.js`：课程范围主题、作者时间、分页 |
| CO-02 | 有实现 | `communication.py:reply_topic`：一级文字回复 |
| CO-03 | 有实现 | `communication.py:delete_topic/delete_reply`：本人/教师/管理员范围、删除标记 |
| CO-04 | 有实现 | `notification_service.py`、`notifications.py`、业务事件及前端跳转：通知、未读、已读 |
| PM-01 | 有实现 | `communication.py:_private_course/_peer/conversation`：本课师生文字私信，管理员拒绝正文访问 |
| PM-02 | 有实现 | `communication.py:_mark_received`、`communication.js`：手动刷新、已读、通知不含私信正文 |
| PR-01 | 有实现 | `learning_service.py:get_course_progress`：有效章节集合、百分比、播放位置与重复完成 |
| PR-02 | 有实现 | `homework.js`、`exams.js`：本人作业状态、考试尝试及最终结果 |
| PR-03 | 有实现 | `learning.py:course_students`、`homework.js`：本人课程学生表、进度、作业及最终考试成绩 |
| PR-04 | 有实现 | `learning_service.py:_notify_completion`、`models/notification.py`：全部章节完成与事件唯一约束 |
| CE-01 | 有实现 | `courses.py:_validate_certificate_exam`、`certificates.js`：本课有效结课考试与发布冻结 |
| CE-02 | 有实现 | `certificates.py:eligibility`：全部章节、必交作业已批、指定考试最终及格 |
| CE-03 | 有实现 | `certificates.py:claim_certificate`、`models/certificate.py`：重新核验、课程锁与唯一证书 |
| CE-04 | 有实现 | `models/certificate.py`、`certificates.js`：颁发时信息快照、教师颁发列表与浏览器打印 |
| SY-01 | 有实现 | `users.py`、`courses.py`：教师/课程审核与审核人、时间、结果字段 |
| SY-02 | 有实现 | `platform.py`、`settings.js`、`auth.py`：平台名称、注册开关、后端同步拒绝 |
| SY-03 | 有实现 | `scripts/backup_restore.py:backup`：数据库与上传文件、版本、时间、清单与摘要 |
| SY-04 | 有实现 | `scripts/backup_restore.py:restore`：明确目标、新空库/目录、文件摘要与数据抽样核对；已有独立恢复证据 |
| SY-05 | 有实现 | `courses.py`、`users.py`：归档、停用、会话撤销及关键依赖保护 |

后端表中省略的目录前缀为 `backend/app/api/v1/`、`backend/app/services/` 或 `backend/app/`；前端脚本在 `backend/static/js/`。

## 尚存问题与交付缺项

1. **CM-02：章节排序缺少页面操作。** 后端 `ChapterCreate/ChapterUpdate` 均有 `sort_order`，列表按顺序展示；但编辑表单不读取、不编辑该字段，新增章节固定用章节数加一。教师不能在网页上调整顺序。应补一个顺序字段或上下移动操作后定向验证。
2. **CM-02：编辑章节的素材刷新错误。** 新增弹窗使用 `@click="loadMedia(chForm.content_type)"`，编辑弹窗仍是 `@click="loadMedia"`。本次执行实际组件 setup 与按钮表达式：初始参数是 `document`，点击刷新后参数类型变为 `object`；`loadMedia` 随后把它传入 `media_type`。这是组件级重现，未冒称本日浏览器实际操作。应显式传入 `editChForm.content_type` 并补编辑弹窗回归。
3. **需求第 8～9 节的正式交付尚不能认定完成。** 仓库有运行脚本、配置、锁定依赖、迁移、测试记录和大量随机 QA 数据生成脚本；未见正式演示数据初始化包、总体设计/ER 图/关键流程图、两人演示分工材料、每人不少于 15 页的实训报告及按课程要求命名的最终附件包。随机测试数据不等同正式演示交付。

本次按用户要求核查并报告这些缺口，产品改动集中于空白简答题规则。

## 空白简答题的新行为

- 漏答、`null`、空字符串、仅空格/制表符/换行/全角空格，以及接口原已接受的空列表：自动 0 分、已批、答案判错；满分仍取整卷快照总分。
- 有内容的简答题维持人工批改；混合答卷只等待这些题，全部完成后发布最终成绩及一次成绩通知。
- 教师页面不显示空白题评分框，也不把它们提交到批改接口；接口拒绝给空白题人工改分。非空题在最终发布前的原有评分行为保留。
- 手动提交及超时读取草稿结算共用逻辑；重复提交不重算、不重复通知。
- 新规则适用于之后的交卷/超时结算；不批量迁移历史已提交或最终成绩，不新增数据库迁移。

## 本次验证与边界

本机项目独立 MySQL 8.4.11，应用 `127.0.0.1:20081`，数据库 `127.0.0.1:3309/campus_learning`。

| 检查 | 结果与证据范围 |
|---|---|
| `scripts/check_blank_short_answers.py` | 30 次真实 HTTP 请求通过；独立命名课程/考试，覆盖全空白、混合、超时、禁止人工改分、重复交卷；提交后新 MySQL 会话重读成绩、逐题已批状态及唯一通知 |
| `scripts/check_stage5.py` | 5 组、76 次真实 HTTP 请求通过；同步用例使“部分阅卷”明确使用非空简答作答，保留客观题漏答与固定满分验证 |
| `scripts/check_blank_short_answers.cjs` | 1 项组件检查通过；执行真实 Vue 与考试组件、编译模板、验证空白评分框隐藏及保存请求仅含非空题；API 为替身，不计真实页面验证 |
| `scripts/check_acceptance_fixes.cjs` | 原有 4 项组件/API 客户端回归通过；不覆盖上述编辑弹窗遗漏 |
| `backend/tests/test_bootstrap.py` | 5 项基础测试通过 |
| 前端语法、diff 空白检查 | 通过 |

本地结果在忽略的 `.runtime/blank-short-answers-results.json` 和 `.runtime/stage5-results.json`。测试账号和令牌不写入共享报告。应用已重启使用新规则。未重跑全部 14 个页面验收场景、证书/备份恢复或跨设备干净安装；旧报告按原日期和环境解释。
