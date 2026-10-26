"""Report API (RPT-01 through RPT-08)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import Perm
from app.core.rbac import load_user_permissions
from app.database import get_db
from app.models.user import User
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


def _check_perm(db: Session, user: User, *perms: str):
    user_perms = load_user_permissions(db, user.id)
    if not any(p in user_perms for p in perms):
        raise HTTPException(403, f"Requires: {', '.join(perms)}")


@router.get("/personal")
def get_personal_report(requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """RPT-01: personal learning report."""
    report = ReportService.personal_report(db, requester.id)
    if not report:
        raise HTTPException(404, "User not found")
    return report


@router.get("/personal/{user_id}")
def get_user_report(user_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """RPT-01: view another user's report (requires user:read)."""
    _check_perm(db, requester, Perm.USER_READ, Perm.REPORT_READ)
    report = ReportService.personal_report(db, user_id)
    if not report:
        raise HTTPException(404, "User not found")
    return report


@router.get("/department/{department_id}")
def get_department_report(department_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """RPT-02: department report."""
    _check_perm(db, requester, Perm.REPORT_READ)
    report = ReportService.department_report(db, department_id)
    if not report:
        raise HTTPException(404, "Department not found or empty")
    return report


@router.get("/course/{course_id}")
def get_course_report(course_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """RPT-03: course report."""
    _check_perm(db, requester, Perm.REPORT_READ)
    report = ReportService.course_report(db, course_id)
    if not report:
        raise HTTPException(404, "Course not found")
    return report


@router.get("/plan/{plan_id}")
def get_plan_report(plan_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """RPT-04: training plan report."""
    _check_perm(db, requester, Perm.REPORT_READ)
    report = ReportService.training_plan_report(db, plan_id)
    if not report:
        raise HTTPException(404, "Plan not found")
    return report


@router.get("/compliance")
def get_compliance_report(
    start_date: str = Query(""),
    end_date: str = Query(""),
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """RPT-08: compliance audit report."""
    _check_perm(db, requester, Perm.REPORT_READ)
    return ReportService.compliance_report(db, start_date, end_date)
