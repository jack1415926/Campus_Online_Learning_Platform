"""Initial campus learning platform schema."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "campus_20261105"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('categories',
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('parent_id', sa.CHAR(length=36), nullable=True),
    sa.Column('level', sa.Integer(), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('description', sa.String(length=500), nullable=True),
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['parent_id'], ['categories.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_categories_name'), 'categories', ['name'], unique=False)
    op.create_index(op.f('ix_categories_parent_id'), 'categories', ['parent_id'], unique=False)
    op.create_table('exams',
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('course_id', sa.String(length=36), nullable=True),
    sa.Column('question_ids', sa.JSON(), nullable=True),
    sa.Column('duration_minutes', sa.Integer(), nullable=False),
    sa.Column('pass_score', sa.Float(), nullable=False),
    sa.Column('max_attempts', sa.Integer(), nullable=False),
    sa.Column('start_time', sa.String(length=50), nullable=True),
    sa.Column('end_time', sa.String(length=50), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_by', sa.String(length=36), nullable=True),
    sa.Column('paper_snapshot', sa.JSON(), nullable=True),
    sa.Column('grading_notes', sa.Text(), nullable=True),
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_exams_course_id'), 'exams', ['course_id'], unique=False)
    op.create_index(op.f('ix_exams_title'), 'exams', ['title'], unique=False)
    op.create_table('media_assets',
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('media_type', sa.Enum('video', 'document', 'image', name='media_type'), nullable=False),
    sa.Column('storage_key', sa.String(length=500), nullable=False),
    sa.Column('file_url', sa.String(length=1000), nullable=True),
    sa.Column('file_size', sa.Integer(), nullable=True),
    sa.Column('mime_type', sa.String(length=100), nullable=True),
    sa.Column('duration', sa.Integer(), nullable=True),
    sa.Column('resolution', sa.String(length=20), nullable=True),
    sa.Column('category_id', sa.String(length=36), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('uploaded_by', sa.String(length=36), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_media_assets_category_id'), 'media_assets', ['category_id'], unique=False)
    op.create_index(op.f('ix_media_assets_media_type'), 'media_assets', ['media_type'], unique=False)
    op.create_index(op.f('ix_media_assets_name'), 'media_assets', ['name'], unique=False)
    op.create_index(op.f('ix_media_assets_uploaded_by'), 'media_assets', ['uploaded_by'], unique=False)
    op.create_table('media_categories',
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_by', sa.String(length=36), nullable=True),
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_media_categories_name'), 'media_categories', ['name'], unique=False)
    op.create_table('notifications',
    sa.Column('event_key', sa.String(length=180), nullable=True),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('notification_type', sa.Enum('system', 'course_reminder', 'exam_reminder', 'assignment', 'certificate', name='notif_type'), nullable=False),
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('channel', sa.Enum('in_app', name='notif_channel'), nullable=False),
    sa.Column('status', sa.Enum('pending', 'sent', 'failed', name='notif_status'), nullable=False),
    sa.Column('is_read', sa.Boolean(), nullable=False),
    sa.Column('sent_at', sa.String(length=50), nullable=True),
    sa.Column('extra_data', sa.JSON(), nullable=True),
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('event_key', name='uq_notification_event')
    )
    op.create_index(op.f('ix_notifications_is_read'), 'notifications', ['is_read'], unique=False)
    op.create_index(op.f('ix_notifications_notification_type'), 'notifications', ['notification_type'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.create_table('permissions',
    sa.Column('code', sa.String(length=100), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('module', sa.String(length=50), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_permissions_code'), 'permissions', ['code'], unique=True)
    op.create_index(op.f('ix_permissions_module'), 'permissions', ['module'], unique=False)
    op.create_table('platform_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('platform_name', sa.String(length=100), nullable=False),
    sa.Column('registration_open', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('question_banks',
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_by', sa.String(length=36), nullable=True),
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_question_banks_name'), 'question_banks', ['name'], unique=False)
    op.create_table('questions',
    sa.Column('question_type', sa.Enum('single_choice', 'multiple_choice', 'true_false', 'short_answer', name='question_type'), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('options', sa.JSON(), nullable=True),
    sa.Column('correct_answer', sa.JSON(), nullable=True),
    sa.Column('explanation', sa.Text(), nullable=True),
    sa.Column('difficulty', sa.Integer(), nullable=False),
    sa.Column('knowledge_point', sa.String(length=200), nullable=True),
    sa.Column('score', sa.Float(), nullable=False),
    sa.Column('is_objective', sa.Boolean(), nullable=False),
    sa.Column('created_by', sa.String(length=36), nullable=True),
    sa.Column('question_bank_id', sa.String(length=36), nullable=True),
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_questions_knowledge_point'), 'questions', ['knowledge_point'], unique=False)
    op.create_index(op.f('ix_questions_question_bank_id'), 'questions', ['question_bank_id'], unique=False)
    op.create_index(op.f('ix_questions_question_type'), 'questions', ['question_type'], unique=False)
    op.create_table('roles',
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('is_builtin', sa.Boolean(), nullable=False),
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_roles_code'), 'roles', ['code'], unique=True)
    op.create_table('sessions',
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('token', sa.String(length=128), nullable=False),
    sa.Column('client_info', sa.String(length=500), nullable=True),
    sa.Column('status', sa.Enum('active', 'revoked', 'expired', name='session_status'), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_active_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sessions_status'), 'sessions', ['status'], unique=False)
    op.create_index(op.f('ix_sessions_token'), 'sessions', ['token'], unique=True)
    op.create_index(op.f('ix_sessions_user_id'), 'sessions', ['user_id'], unique=False)
    op.create_table('users',
    sa.Column('username', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=True),
    sa.Column('full_name', sa.String(length=100), nullable=False),
    sa.Column('requested_role', sa.String(length=20), server_default='student', nullable=False),
    sa.Column('teacher_review_status', sa.String(length=20), nullable=True),
    sa.Column('teacher_review_reason', sa.Text(), nullable=True),
    sa.Column('teacher_reviewed_by', sa.CHAR(length=36), nullable=True),
    sa.Column('teacher_reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('phone', sa.String(length=30), nullable=True),
    sa.Column('avatar_url', sa.String(length=500), nullable=True),
    sa.Column('status', sa.Enum('active', 'inactive', 'suspended', name='user_status'), nullable=False),
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_table('courses',
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('cover_image_url', sa.String(length=1000), nullable=True),
    sa.Column('category_id', sa.CHAR(length=36), nullable=True),
    sa.Column('difficulty', sa.Enum('beginner', 'intermediate', 'advanced', name='difficulty'), nullable=False),
    sa.Column('estimated_minutes', sa.Integer(), nullable=False),
    sa.Column('instructor', sa.String(length=100), nullable=True),
    sa.Column('status', sa.Enum('draft', 'pending_review', 'published', 'archived', name='course_status'), nullable=False),
    sa.Column('certificate_exam_id', sa.CHAR(length=36), nullable=True),
    sa.Column('created_by', sa.String(length=36), nullable=True),
    sa.Column('review_reason', sa.Text(), nullable=True),
    sa.Column('reviewed_by', sa.CHAR(length=36), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_courses_category_id'), 'courses', ['category_id'], unique=False)
    op.create_index(op.f('ix_courses_status'), 'courses', ['status'], unique=False)
    op.create_index(op.f('ix_courses_title'), 'courses', ['title'], unique=False)
    op.create_table('exam_records',
    sa.Column('question_snapshot', sa.JSON(), nullable=True),
    sa.Column('draft_answers', sa.JSON(), nullable=True),
    sa.Column('deadline_at', sa.String(length=50), nullable=True),
    sa.Column('pass_percent', sa.Float(), nullable=True),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('exam_id', sa.String(length=36), nullable=False),
    sa.Column('answers', sa.JSON(), nullable=True),
    sa.Column('total_score', sa.Float(), nullable=False),
    sa.Column('max_score', sa.Float(), nullable=False),
    sa.Column('is_pass', sa.Boolean(), nullable=True),
    sa.Column('status', sa.Enum('not_started', 'in_progress', 'submitted', 'graded', name='exam_record_status'), nullable=False),
    sa.Column('started_at', sa.String(length=50), nullable=True),
    sa.Column('submitted_at', sa.String(length=50), nullable=True),
    sa.Column('graded_at', sa.String(length=50), nullable=True),
    sa.Column('graded_by', sa.String(length=36), nullable=True),
    sa.Column('attempt_number', sa.Integer(), nullable=False),
    sa.Column('time_spent_seconds', sa.Integer(), nullable=True),
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['exam_id'], ['exams.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('exam_id', 'user_id', 'attempt_number', name='uq_exam_attempt')
    )
    op.create_index(op.f('ix_exam_records_exam_id'), 'exam_records', ['exam_id'], unique=False)
    op.create_index(op.f('ix_exam_records_user_id'), 'exam_records', ['user_id'], unique=False)
    op.create_table('role_permissions',
    sa.Column('role_id', sa.CHAR(length=36), nullable=False),
    sa.Column('permission_id', sa.CHAR(length=36), nullable=False),
    sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )
    op.create_table('user_roles',
    sa.Column('user_id', sa.CHAR(length=36), nullable=False),
    sa.Column('role_id', sa.CHAR(length=36), nullable=False),
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_roles_role_id'), 'user_roles', ['role_id'], unique=False)
    op.create_index(op.f('ix_user_roles_user_id'), 'user_roles', ['user_id'], unique=False)
    op.create_table('certificates',
    sa.Column('course_id', sa.CHAR(length=36), nullable=False),
    sa.Column('user_id', sa.CHAR(length=36), nullable=False),
    sa.Column('exam_record_id', sa.CHAR(length=36), nullable=False),
    sa.Column('number', sa.String(length=50), nullable=False),
    sa.Column('student_name', sa.String(length=100), nullable=False),
    sa.Column('course_title', sa.String(length=255), nullable=False),
    sa.Column('platform_name', sa.String(length=100), nullable=False),
    sa.Column('issued_at', sa.DateTime(), nullable=False),
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['exam_record_id'], ['exam_records.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('course_id', 'user_id', name='uq_certificate_student_course'),
    sa.UniqueConstraint('number')
    )
    op.create_index(op.f('ix_certificates_course_id'), 'certificates', ['course_id'], unique=False)
    op.create_index(op.f('ix_certificates_user_id'), 'certificates', ['user_id'], unique=False)
    op.create_table('chapters',
    sa.Column('course_id', sa.CHAR(length=36), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('content_type', sa.Enum('video', 'document', 'text', 'image', name='content_type'), nullable=False),
    sa.Column('content_ref_id', sa.CHAR(length=36), nullable=True),
    sa.Column('text_content', sa.Text(), nullable=True),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('is_required', sa.Boolean(), nullable=False),
    sa.Column('estimated_minutes', sa.Integer(), nullable=False),
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chapters_course_id'), 'chapters', ['course_id'], unique=False)
    op.create_table('course_assignments',
    sa.Column('course_id', sa.CHAR(length=36), nullable=False),
    sa.Column('assignment_type', sa.Enum('user', name='assignment_type'), nullable=False),
    sa.Column('target_id', sa.String(length=36), nullable=False),
    sa.Column('deadline', sa.String(length=50), nullable=True),
    sa.Column('is_required', sa.Boolean(), nullable=False),
    sa.Column('assigned_by', sa.CHAR(length=36), nullable=True),
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('course_id', 'assignment_type', 'target_id', name='uq_course_assignment_target')
    )
    op.create_index(op.f('ix_course_assignments_course_id'), 'course_assignments', ['course_id'], unique=False)
    op.create_index(op.f('ix_course_assignments_target_id'), 'course_assignments', ['target_id'], unique=False)
    op.create_table('discussion_topics',
    sa.Column('course_id', sa.CHAR(length=36), nullable=False),
    sa.Column('user_id', sa.CHAR(length=36), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.Column('deleted_by', sa.CHAR(length=36), nullable=True),
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_discussion_topics_course_id'), 'discussion_topics', ['course_id'], unique=False)
    op.create_table('homeworks',
    sa.Column('course_id', sa.CHAR(length=36), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('due_at', sa.DateTime(), nullable=False),
    sa.Column('max_score', sa.Float(), nullable=False),
    sa.Column('grading_notes', sa.Text(), nullable=False),
    sa.Column('is_required', sa.Boolean(), nullable=False),
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_homeworks_course_id'), 'homeworks', ['course_id'], unique=False)
    op.create_table('learning_records',
    sa.Column('user_id', sa.CHAR(length=36), nullable=False),
    sa.Column('course_id', sa.CHAR(length=36), nullable=False),
    sa.Column('chapter_id', sa.CHAR(length=36), nullable=True),
    sa.Column('learning_seconds', sa.Integer(), nullable=False),
    sa.Column('progress_percent', sa.Float(), nullable=False),
    sa.Column('resume_position', sa.JSON(), nullable=True),
    sa.Column('status', sa.Enum('not_started', 'in_progress', 'completed', 'overdue', name='completion_status'), nullable=False),
    sa.Column('started_at', sa.String(length=50), nullable=True),
    sa.Column('completed_at', sa.String(length=50), nullable=True),
    sa.Column('last_accessed_at', sa.String(length=50), nullable=True),
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'course_id', 'chapter_id', name='uq_learning_user_chapter')
    )
    op.create_index(op.f('ix_learning_records_chapter_id'), 'learning_records', ['chapter_id'], unique=False)
    op.create_index(op.f('ix_learning_records_course_id'), 'learning_records', ['course_id'], unique=False)
    op.create_index(op.f('ix_learning_records_user_id'), 'learning_records', ['user_id'], unique=False)
    op.create_table('private_messages',
    sa.Column('course_id', sa.CHAR(length=36), nullable=False),
    sa.Column('sender_id', sa.CHAR(length=36), nullable=False),
    sa.Column('recipient_id', sa.CHAR(length=36), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('read_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_private_messages_course_id'), 'private_messages', ['course_id'], unique=False)
    op.create_index(op.f('ix_private_messages_recipient_id'), 'private_messages', ['recipient_id'], unique=False)
    op.create_index(op.f('ix_private_messages_sender_id'), 'private_messages', ['sender_id'], unique=False)
    op.create_table('discussion_replies',
    sa.Column('topic_id', sa.CHAR(length=36), nullable=False),
    sa.Column('user_id', sa.CHAR(length=36), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.Column('deleted_by', sa.CHAR(length=36), nullable=True),
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.ForeignKeyConstraint(['topic_id'], ['discussion_topics.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_discussion_replies_topic_id'), 'discussion_replies', ['topic_id'], unique=False)
    op.create_table('homework_submissions',
    sa.Column('homework_id', sa.CHAR(length=36), nullable=False),
    sa.Column('user_id', sa.CHAR(length=36), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('attachment_key', sa.String(length=500), nullable=True),
    sa.Column('attachment_name', sa.String(length=255), nullable=True),
    sa.Column('attachment_mime', sa.String(length=100), nullable=True),
    sa.Column('submitted_at', sa.DateTime(), nullable=False),
    sa.Column('score', sa.Float(), nullable=True),
    sa.Column('feedback', sa.Text(), nullable=True),
    sa.Column('graded_by', sa.CHAR(length=36), nullable=True),
    sa.Column('graded_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.CHAR(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['homework_id'], ['homeworks.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('homework_id', 'user_id', name='uq_homework_student')
    )
    op.create_index(op.f('ix_homework_submissions_homework_id'), 'homework_submissions', ['homework_id'], unique=False)
    op.create_index(op.f('ix_homework_submissions_user_id'), 'homework_submissions', ['user_id'], unique=False)


def downgrade():
    op.drop_table('homework_submissions')
    op.drop_table('discussion_replies')
    op.drop_table('private_messages')
    op.drop_table('learning_records')
    op.drop_table('homeworks')
    op.drop_table('discussion_topics')
    op.drop_table('course_assignments')
    op.drop_table('chapters')
    op.drop_table('certificates')
    op.drop_table('user_roles')
    op.drop_table('role_permissions')
    op.drop_table('exam_records')
    op.drop_table('courses')
    op.drop_table('users')
    op.drop_table('sessions')
    op.drop_table('roles')
    op.drop_table('questions')
    op.drop_table('question_banks')
    op.drop_table('platform_settings')
    op.drop_table('permissions')
    op.drop_table('notifications')
    op.drop_table('media_categories')
    op.drop_table('media_assets')
    op.drop_table('exams')
    op.drop_table('categories')
