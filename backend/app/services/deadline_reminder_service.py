"""Deadline reminder service (time-triggered).

Periodically scans course assignments that carry a deadline and sends an
in-app reminder to affected users:
  - ~7 days before the deadline ("一周后到期")
  - on the last day / overdue ("最后一天")

Reminders are idempotent: each phase is sent at most once per assignment+user,
tracked via the notification extra_data.
"""

import logging
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.learning import CourseAssignment, LearningRecord, CompletionStatus
from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.services.learning_service import AssignmentService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

# Reminder phase keys stored in extra_data so each phase fires only once.
PHASE_ONE_WEEK = "7d"
PHASE_LAST_DAY = "1d"


def _parse_deadline(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _already_reminded(db: Session, user_id: str, assignment_id: str, phase: str) -> bool:
    notifs = db.execute(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.extra_data.isnot(None),
        )
    ).scalars().all()
    for n in notifs:
        if n.extra_data and n.extra_data.get("assignment_id") == assignment_id \
                and n.extra_data.get("reminder") == phase:
            return True
    return False


def _has_completed(db: Session, user_id: str, course_id: str) -> bool:
    stmt = select(LearningRecord).where(
        LearningRecord.user_id == user_id,
        LearningRecord.course_id == course_id,
        LearningRecord.status == CompletionStatus.completed,
    )
    return db.execute(stmt).scalars().first() is not None


def check_and_notify(db: Session) -> int:
    """Scan assignments with deadlines and send due reminders.

    Returns the number of notifications created.
    """
    today = date.today()
    created = 0

    assignments = db.execute(
        select(CourseAssignment).where(CourseAssignment.deadline.isnot(None))
    ).scalars().all()

    for assignment in assignments:
        deadline = _parse_deadline(assignment.deadline)
        if deadline is None:
            continue
        days_left = (deadline - today).days

        # Determine which phase applies (overdue counts as the last day).
        phase = None
        if days_left <= 7:
            phase = PHASE_ONE_WEEK
        if days_left <= 0:
            phase = PHASE_LAST_DAY
        if phase is None:
            continue

        course = db.execute(
            select(Course).where(Course.id == assignment.course_id)
        ).scalar_one_or_none()
        course_title = course.title if course else assignment.course_id
        deadline_txt = deadline.isoformat()

        if phase == PHASE_LAST_DAY:
            title = "课程即将截止"
            body = f"课程《{course_title}》将在今天 {deadline_txt} 截止，请尽快完成学习！"
        else:
            title = "课程即将到期"
            body = f"课程《{course_title}》将在 {deadline_txt} 到期（还剩 {days_left} 天），请合理安排时间完成学习。"

        for user in AssignmentService.resolve_target_users(db, assignment):
            if _has_completed(db, user.id, assignment.course_id):
                continue
            if _already_reminded(db, user.id, assignment.id, phase):
                continue
            NotificationService.notify_user(
                db, user.id, NotificationType.course_reminder, title, body,
                extra_data={"assignment_id": assignment.id, "reminder": phase,
                            "course_id": assignment.course_id},
            )
            created += 1

    if created:
        db.commit()
        logger.info("Deadline reminder: created %d notifications", created)
    return created
