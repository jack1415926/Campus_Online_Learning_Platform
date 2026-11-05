"""Category totals and asset lists must use the same ownership boundary."""

import os
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

with patch.dict(os.environ, {
    "DATABASE_URL": "mysql+pymysql://test:test@127.0.0.1:1/test_media",
    "SECRET_KEY": "media-tests-only-not-a-deployment-secret",
}):
    from app.api.v1.media import list_media, list_media_categories
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


if __name__ == "__main__":
    unittest.main()
