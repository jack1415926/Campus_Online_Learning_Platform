"""Category totals and asset lists must use the same ownership boundary."""

import os
import asyncio
import io
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile

with patch.dict(os.environ, {
    "DATABASE_URL": "mysql+pymysql://test:test@127.0.0.1:1/test_media",
    "SECRET_KEY": "media-tests-only-not-a-deployment-secret",
}):
    from app.api.v1.media import (
        list_media, list_media_categories, create_media_category,
        update_media_category, delete_media_category, upload_media,
    )
    from app.schemas.media import MediaCategoryCreate, MediaCategoryUpdate
    from app.services import storage_service
    from app.core.seed import assign_role, seed_rbac
    from app.models import Base, MediaAsset, MediaCategory, MediaType, Permission, Role, User, UserRole, role_permissions


class MediaVisibilityTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine, tables=[
            User.__table__, Role.__table__, Permission.__table__,
            UserRole.__table__, role_permissions,
            MediaCategory.__table__, MediaAsset.__table__,
        ])
        self.db = Session(self.engine)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.db.close)
        seed_rbac(self.db)
        self.teacher = User(username="teacher_a", email="a@example.test", full_name="Teacher A")
        self.other = User(username="teacher_b", email="b@example.test", full_name="Teacher B")
        self.admin = User(username="admin", email="admin@example.test", full_name="Administrator")
        self.category = MediaCategory(name="Course materials")
        self.empty = MediaCategory(name="Empty category")
        self.db.add_all([self.teacher, self.other, self.admin, self.category, self.empty])
        self.db.flush()
        for user, role in [(self.teacher, "teacher"), (self.other, "teacher"), (self.admin, "admin")]:
            assign_role(self.db, user, role)
        for index, user in enumerate([self.teacher, self.other, self.other]):
            self.db.add(MediaAsset(name=f"material-{index}.pdf", storage_key=f"test/{index}.pdf",
                                   media_type=MediaType.document, category_id=self.category.id,
                                   uploaded_by=str(user.id)))
        self.db.commit()

    def assert_counts(self, user, expected):
        categories = {item.id: item.asset_count for item in list_media_categories(requester=user, db=self.db)}
        response = list_media(media_type=None, category_id=self.category.id, keyword=None,
                              page=1, page_size=100, requester=user, db=self.db)
        self.assertEqual(response.meta.total, expected)
        self.assertEqual(categories[self.category.id], response.meta.total)
        self.assertEqual(categories[self.empty.id], 0)

    def test_teachers_count_only_their_own_assets(self):
        self.assert_counts(self.teacher, 1)
        self.assert_counts(self.other, 2)

    def test_administrator_counts_all_assets(self):
        self.assert_counts(self.admin, 3)

    def test_teacher_manages_own_category_and_delete_preserves_files(self):
        category = create_media_category(MediaCategoryCreate(name="Teacher materials"), self.teacher, self.db)
        updated = update_media_category(category.id, MediaCategoryUpdate(name="Renamed"), self.teacher, self.db)
        self.assertEqual(updated.name, "Renamed")
        asset = MediaAsset(name="keep.pdf", storage_key="keep.pdf", media_type=MediaType.document,
                           category_id=category.id, uploaded_by=str(self.teacher.id))
        self.db.add(asset)
        self.db.commit()
        delete_media_category(category.id, self.teacher, self.db)
        self.assertIsNone(self.db.get(MediaAsset, asset.id).category_id)

    def test_teacher_cannot_change_another_teachers_category(self):
        self.category.created_by = str(self.other.id)
        self.db.commit()
        for operation in [
            lambda: update_media_category(self.category.id, MediaCategoryUpdate(name="Denied"), self.teacher, self.db),
            lambda: delete_media_category(self.category.id, self.teacher, self.db),
        ]:
            with self.assertRaises(HTTPException) as error:
                operation()
            self.assertEqual(error.exception.status_code, 403)
        update_media_category(self.category.id, MediaCategoryUpdate(name="Admin edit"), self.admin, self.db)

    def test_teacher_cannot_unassign_another_teachers_files_by_deleting_category(self):
        self.category.created_by = str(self.teacher.id)
        self.db.commit()
        with self.assertRaises(HTTPException) as error:
            delete_media_category(self.category.id, self.teacher, self.db)
        self.assertEqual(error.exception.status_code, 409)

    def test_student_cannot_create_category(self):
        student = User(username="student", email="student@example.test", full_name="Student")
        self.db.add(student)
        self.db.flush()
        assign_role(self.db, student, "student")
        with self.assertRaises(HTTPException) as error:
            create_media_category(MediaCategoryCreate(name="Denied"), student, self.db)
        self.assertEqual(error.exception.status_code, 403)

    def test_teacher_can_upload_without_a_category(self):
        runtime = Path(__file__).resolve().parents[2] / ".runtime"
        runtime.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=runtime) as directory, patch.object(storage_service, "STORAGE_DIR", directory):
            self.assertTrue(Path(directory).resolve().is_relative_to(runtime.resolve()))
            file = UploadFile(filename="lesson.pdf", file=io.BytesIO(b"%PDF-1.4\nlocal test"))
            asset = asyncio.run(upload_media(file=file, category_id=None, description=None,
                                             requester=self.teacher, db=self.db))
            self.assertIsNone(asset.category_id)
            self.assertEqual(str(asset.uploaded_by), str(self.teacher.id))


if __name__ == "__main__":
    unittest.main()
