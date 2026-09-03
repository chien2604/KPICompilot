"""Add the auditable monthly and quarterly KPI workflow without resetting data."""

import sys
from pathlib import Path

from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import db.models  # noqa: E402,F401
from db.database import Base, engine  # noqa: E402
from db.models.kpi import AuditLog  # noqa: E402

PRESERVED_TABLES = (
    "departments",
    "users",
    "work_catalog_items",
    "tasks",
    "task_assignments",
    "task_evidences",
    "kpi_scores",
)


def _workflow_schema_exists(connection) -> bool:
    """Return whether migration 005 columns existed before this process started."""

    required_columns = (
        ("users", "organization_domain"),
        ("task_assignments", "quality_status"),
        ("task_evidences", "verification_status"),
        ("kpi_scores", "score_status"),
    )
    for table_name, column_name in required_columns:
        exists = connection.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = :table_name
                      AND column_name = :column_name
                )
                """
            ),
            {"table_name": table_name, "column_name": column_name},
        ).scalar_one()
        if not exists:
            return False
    return True


def _count_rows(connection) -> dict[str, int]:
    """Return row counts that must remain unchanged during this migration."""

    return {
        table_name: connection.execute(
            text(f"SELECT COUNT(*) FROM {table_name}")
        ).scalar_one()
        for table_name in PRESERVED_TABLES
    }


def _assert_no_duplicate_codes(connection) -> None:
    """Stop before migration when organization or catalog codes are ambiguous."""

    checks = {
        "departments.code": "SELECT code FROM departments GROUP BY code HAVING COUNT(*) > 1 LIMIT 1",
        "work_catalog_items.code": "SELECT code FROM work_catalog_items GROUP BY code HAVING COUNT(*) > 1 LIMIT 1",
    }
    for label, query in checks.items():
        duplicate = connection.execute(text(query)).scalar_one_or_none()
        if duplicate is not None:
            raise RuntimeError(f"Migration stopped: duplicate {label}={duplicate!r}.")


def _assert_no_orphans(connection) -> None:
    """Stop when existing foreign-key relationships contain orphan records."""

    checks = {
        "users.department_id": """
            SELECT COUNT(*) FROM users AS child
            LEFT JOIN departments AS parent ON parent.id = child.department_id
            WHERE child.department_id IS NOT NULL AND parent.id IS NULL
        """,
        "tasks.creator_id": """
            SELECT COUNT(*) FROM tasks AS child
            LEFT JOIN users AS parent ON parent.id = child.creator_id
            WHERE child.creator_id IS NOT NULL AND parent.id IS NULL
        """,
        "task_assignments.task_id": """
            SELECT COUNT(*) FROM task_assignments AS child
            LEFT JOIN tasks AS parent ON parent.id = child.task_id
            WHERE parent.id IS NULL
        """,
        "task_assignments.user_id": """
            SELECT COUNT(*) FROM task_assignments AS child
            LEFT JOIN users AS parent ON parent.id = child.user_id
            WHERE parent.id IS NULL
        """,
        "task_evidences.task_id": """
            SELECT COUNT(*) FROM task_evidences AS child
            LEFT JOIN tasks AS parent ON parent.id = child.task_id
            WHERE parent.id IS NULL
        """,
        "kpi_scores.user_id": """
            SELECT COUNT(*) FROM kpi_scores AS child
            LEFT JOIN users AS parent ON parent.id = child.user_id
            WHERE parent.id IS NULL
        """,
    }
    for label, query in checks.items():
        orphan_count = connection.execute(text(query)).scalar_one()
        if orphan_count:
            raise RuntimeError(
                f"Migration stopped: {orphan_count} orphan rows at {label}."
            )


def _add_columns_and_indexes(connection) -> None:
    """Add backward-compatible columns required by the new workflow."""

    statements = (
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS organization_domain VARCHAR(30) NOT NULL DEFAULT 'UBND'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS manager_id INTEGER REFERENCES users(id)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS management_scope_json JSONB NOT NULL DEFAULT '{}'::jsonb",
        "ALTER TABLE work_catalog_items ADD COLUMN IF NOT EXISTS legal_source VARCHAR(255) NOT NULL DEFAULT 'Quyết định 283/QĐ-UBND'",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS catalog_code_snapshot VARCHAR(40)",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS catalog_name_snapshot VARCHAR(500)",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS expected_output_snapshot VARCHAR(500)",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS complexity_group_snapshot VARCHAR(10)",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS catalog_score_snapshot DOUBLE PRECISION",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS conversion_factor_snapshot DOUBLE PRECISION",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS assignment_authority VARCHAR(80)",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS position_scope VARCHAR(255)",
        "ALTER TABLE task_assignments ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'NOT_STARTED'",
        "ALTER TABLE task_assignments ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMP",
        "ALTER TABLE task_assignments ADD COLUMN IF NOT EXISTS quality_status VARCHAR(20) NOT NULL DEFAULT 'PENDING'",
        "ALTER TABLE task_assignments ADD COLUMN IF NOT EXISTS objective_quality_exception BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE task_assignments ADD COLUMN IF NOT EXISTS quality_exception_reason TEXT",
        "ALTER TABLE task_assignments ADD COLUMN IF NOT EXISTS quality_exception_supporting_record TEXT",
        "ALTER TABLE task_assignments ADD COLUMN IF NOT EXISTS quality_exception_verified_by INTEGER REFERENCES users(id)",
        "ALTER TABLE task_assignments ADD COLUMN IF NOT EXISTS quality_exception_verified_at TIMESTAMP",
        "ALTER TABLE task_assignments ADD COLUMN IF NOT EXISTS objective_delay_exception BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE task_assignments ADD COLUMN IF NOT EXISTS delay_exception_reason TEXT",
        "ALTER TABLE task_assignments ADD COLUMN IF NOT EXISTS delay_exception_supporting_record TEXT",
        "ALTER TABLE task_assignments ADD COLUMN IF NOT EXISTS delay_exception_verified_by INTEGER REFERENCES users(id)",
        "ALTER TABLE task_assignments ADD COLUMN IF NOT EXISTS delay_exception_verified_at TIMESTAMP",
        "ALTER TABLE task_assignments ADD COLUMN IF NOT EXISTS result_verified_by INTEGER REFERENCES users(id)",
        "ALTER TABLE task_assignments ADD COLUMN IF NOT EXISTS result_verified_at TIMESTAMP",
        "ALTER TABLE task_assignments ADD COLUMN IF NOT EXISTS result_verification_note TEXT",
        "ALTER TABLE task_evidences ADD COLUMN IF NOT EXISTS assignment_id INTEGER REFERENCES task_assignments(id) ON DELETE CASCADE",
        "ALTER TABLE task_evidences ADD COLUMN IF NOT EXISTS result_type VARCHAR(30) NOT NULL DEFAULT 'PRIMARY_OUTPUT'",
        "ALTER TABLE task_evidences ADD COLUMN IF NOT EXISTS source_type VARCHAR(30) NOT NULL DEFAULT 'FILE_UPLOAD'",
        "ALTER TABLE task_evidences ADD COLUMN IF NOT EXISTS source_system VARCHAR(255)",
        "ALTER TABLE task_evidences ADD COLUMN IF NOT EXISTS source_record_id VARCHAR(255)",
        "ALTER TABLE task_evidences ADD COLUMN IF NOT EXISTS document_number VARCHAR(100)",
        "ALTER TABLE task_evidences ADD COLUMN IF NOT EXISTS issued_date TIMESTAMP",
        "ALTER TABLE task_evidences ADD COLUMN IF NOT EXISTS metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb",
        "ALTER TABLE task_evidences ADD COLUMN IF NOT EXISTS ai_analysis_json JSONB NOT NULL DEFAULT '{}'::jsonb",
        "ALTER TABLE task_evidences ADD COLUMN IF NOT EXISTS file_hash_sha256 VARCHAR(64)",
        "ALTER TABLE task_evidences ADD COLUMN IF NOT EXISTS verification_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT'",
        "ALTER TABLE task_evidences ADD COLUMN IF NOT EXISTS verified_by INTEGER REFERENCES users(id)",
        "ALTER TABLE task_evidences ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP",
        "ALTER TABLE task_evidences ADD COLUMN IF NOT EXISTS verification_note TEXT",
        "ALTER TABLE kpi_assessment_inputs ADD COLUMN IF NOT EXISTS self_scores_json JSONB NOT NULL DEFAULT '{}'::jsonb",
        "ALTER TABLE kpi_assessment_inputs ADD COLUMN IF NOT EXISTS reviewed_scores_json JSONB NOT NULL DEFAULT '{}'::jsonb",
        "ALTER TABLE kpi_assessment_inputs ADD COLUMN IF NOT EXISTS management_review_json JSONB NOT NULL DEFAULT '{}'::jsonb",
        "ALTER TABLE kpi_assessment_inputs ADD COLUMN IF NOT EXISTS self_assessed_at TIMESTAMP",
        "ALTER TABLE kpi_assessment_inputs ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP",
        "ALTER TABLE kpi_assessment_inputs ADD COLUMN IF NOT EXISTS review_note TEXT",
        "ALTER TABLE kpi_scores ADD COLUMN IF NOT EXISTS score_status VARCHAR(20) NOT NULL DEFAULT 'DRAFT'",
        "ALTER TABLE kpi_scores ADD COLUMN IF NOT EXISTS confirmed_by INTEGER REFERENCES users(id)",
        "ALTER TABLE kpi_scores ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMP",
        "CREATE INDEX IF NOT EXISTS ix_users_organization_domain ON users (organization_domain)",
        "CREATE INDEX IF NOT EXISTS ix_users_manager_id ON users (manager_id)",
        "CREATE INDEX IF NOT EXISTS ix_task_assignments_status ON task_assignments (status)",
        "CREATE INDEX IF NOT EXISTS ix_task_evidences_assignment_id ON task_evidences (assignment_id)",
        "CREATE INDEX IF NOT EXISTS ix_task_evidences_file_hash_sha256 ON task_evidences (file_hash_sha256)",
        "CREATE INDEX IF NOT EXISTS ix_task_evidences_verification_status ON task_evidences (verification_status)",
        "CREATE INDEX IF NOT EXISTS ix_kpi_scores_score_status ON kpi_scores (score_status)",
    )
    for statement in statements:
        connection.execute(text(statement))


def _backfill_organization(connection) -> None:
    """Separate UBND authority, HĐND, system, and out-of-scope personnel."""

    leadership_department = connection.execute(
        text(
            """
            SELECT id, parent_id
            FROM departments
            WHERE code IN ('LANH_DAO_HDND_UBND', 'LANH_DAO_UBND')
            ORDER BY CASE WHEN code = 'LANH_DAO_UBND' THEN 0 ELSE 1 END
            LIMIT 1
            """
        )
    ).mappings().first()
    if leadership_department is None:
        return

    leadership_id = leadership_department["id"]
    parent_id = leadership_department["parent_id"]
    connection.execute(
        text(
            """
            UPDATE departments
            SET code = 'LANH_DAO_UBND',
                name = 'Lãnh đạo UBND xã',
                unit_type = 'AUTHORITY'
            WHERE id = :department_id
            """
        ),
        {"department_id": leadership_id},
    )
    hdnd_id = connection.execute(
        text(
            """
            INSERT INTO departments (name, code, unit_type, parent_id)
            VALUES ('Hội đồng nhân dân xã', 'HDND_XA', 'OUT_OF_SCOPE', :parent_id)
            ON CONFLICT (code) DO UPDATE SET
                name = EXCLUDED.name,
                unit_type = EXCLUDED.unit_type,
                parent_id = EXCLUDED.parent_id
            RETURNING id
            """
        ),
        {"parent_id": parent_id},
    ).scalar_one()
    connection.execute(
        text(
            """
            UPDATE users
            SET department_id = :hdnd_id,
                organization_domain = 'HDND',
                organization_role = 'OUT_OF_SCOPE',
                personnel_type = 'CAN_BO',
                is_kpi_eligible = FALSE,
                manager_id = NULL,
                management_scope_json = '{}'::jsonb
            WHERE department_id = :leadership_id
              AND COALESCE(position_title, '') NOT ILIKE '%UBND%'
            """
        ),
        {"hdnd_id": hdnd_id, "leadership_id": leadership_id},
    )
    connection.execute(
        text(
            """
            UPDATE users
            SET organization_domain = 'UBND',
                organization_role = 'UBND_AUTHORITY',
                personnel_type = 'CAN_BO',
                is_kpi_eligible = FALSE,
                manager_id = NULL,
                management_scope_json = '{}'::jsonb
            WHERE department_id = :leadership_id
            """
        ),
        {"leadership_id": leadership_id},
    )
    connection.execute(
        text(
            """
            UPDATE users
            SET organization_domain = 'SYSTEM',
                organization_role = 'SYSTEM_ADMIN',
                is_kpi_eligible = FALSE,
                manager_id = NULL,
                management_scope_json = '{}'::jsonb
            WHERE LOWER(role) = 'admin'
            """
        )
    )
    connection.execute(
        text(
            """
            UPDATE users AS personnel
            SET organization_domain = 'OUT_OF_UBND_KPI_SCOPE',
                organization_role = 'OUT_OF_SCOPE',
                is_kpi_eligible = FALSE,
                manager_id = NULL,
                management_scope_json = '{}'::jsonb
            FROM departments AS department
            WHERE department.id = personnel.department_id
              AND department.code IN (
                  'TRUNG_TAM_CUDVC',
                  'TRUNG_TAM_CUNG_UNG_DICH_VU_CONG'
              )
            """
        )
    )

    authority_id = connection.execute(
        text(
            """
            SELECT id FROM users
            WHERE department_id = :leadership_id
              AND organization_role = 'UBND_AUTHORITY'
              AND (
                  COALESCE(position_title, '') ILIKE '%Chủ tịch UBND%'
                  OR COALESCE(position_title, '') ILIKE 'CT UBND%'
              )
              AND COALESCE(position_title, '') NOT ILIKE '%Phó%'
            ORDER BY id
            LIMIT 1
            """
        ),
        {"leadership_id": leadership_id},
    ).scalar_one_or_none()
    if authority_id is None:
        return

    connection.execute(
        text(
            """
            UPDATE users
            SET manager_id = :authority_id,
                management_scope_json = '{"all_department": true}'::jsonb
            WHERE organization_domain = 'UBND'
              AND organization_role = 'UNIT_HEAD'
              AND is_kpi_eligible = TRUE
            """
        ),
        {"authority_id": authority_id},
    )
    connection.execute(
        text(
            """
            UPDATE users AS personnel
            SET manager_id = (
                SELECT head.id
                FROM users AS head
                WHERE head.department_id = personnel.department_id
                  AND head.organization_role = 'UNIT_HEAD'
                  AND head.is_kpi_eligible = TRUE
                ORDER BY head.id
                LIMIT 1
            )
            WHERE personnel.organization_domain = 'UBND'
              AND personnel.is_kpi_eligible = TRUE
              AND personnel.organization_role IN ('UNIT_DEPUTY', 'SPECIALIST')
              AND EXISTS (
                  SELECT 1
                  FROM users AS head
                  WHERE head.department_id = personnel.department_id
                    AND head.organization_role = 'UNIT_HEAD'
                    AND head.is_kpi_eligible = TRUE
              )
            """
        )
    )
    connection.execute(
        text(
            """
            UPDATE users AS deputy
            SET management_scope_json = CASE
                WHEN COALESCE(deputy.position_title, '') ILIKE '%Phụ trách chung%'
                    THEN '{"all_department": true}'::jsonb
                ELSE jsonb_build_object(
                    'all_department', FALSE,
                    'work_area_codes', COALESCE((
                        SELECT jsonb_agg(area.area_code ORDER BY area.area_code)
                        FROM user_work_areas AS area
                        WHERE area.user_id = deputy.id
                    ), '[]'::jsonb)
                )
            END
            WHERE deputy.organization_role = 'UNIT_DEPUTY'
              AND deputy.organization_domain = 'UBND'
            """
        )
    )


def _backfill_workflow(connection) -> None:
    """Populate immutable snapshots and conservative workflow states."""

    connection.execute(
        text(
            """
            UPDATE tasks AS task
            SET catalog_code_snapshot = COALESCE(task.catalog_code_snapshot, catalog.code),
                catalog_name_snapshot = COALESCE(task.catalog_name_snapshot, catalog.name),
                expected_output_snapshot = COALESCE(task.expected_output_snapshot, catalog.output),
                complexity_group_snapshot = COALESCE(task.complexity_group_snapshot, catalog.complexity_group),
                catalog_score_snapshot = COALESCE(task.catalog_score_snapshot, catalog.conversion_score),
                conversion_factor_snapshot = COALESCE(task.conversion_factor_snapshot, catalog.conversion_factor),
                assignment_authority = COALESCE(
                    task.assignment_authority,
                    (SELECT creator.organization_role FROM users AS creator WHERE creator.id = task.creator_id)
                )
            FROM work_catalog_items AS catalog
            WHERE catalog.id = task.work_catalog_item_id
            """
        )
    )
    connection.execute(
        text(
            """
            UPDATE task_assignments AS assignment
            SET status = CASE
                    WHEN task.status = 'COMPLETED' THEN 'VERIFIED'
                    WHEN assignment.progress_percent >= 100 THEN 'SUBMITTED'
                    WHEN assignment.progress_percent > 0 THEN 'IN_PROGRESS'
                    ELSE 'NOT_STARTED'
                END,
                submitted_at = CASE
                    WHEN task.status = 'COMPLETED' OR assignment.progress_percent >= 100
                        THEN COALESCE(task.completed_at, task.updated_at)
                    ELSE assignment.submitted_at
                END,
                quality_status = CASE
                    WHEN task.status = 'COMPLETED' THEN 'PASS'
                    ELSE 'PENDING'
                END,
                result_verified_at = CASE
                    WHEN task.status = 'COMPLETED' THEN COALESCE(task.completed_at, task.updated_at)
                    ELSE assignment.result_verified_at
                END
            FROM tasks AS task
            WHERE task.id = assignment.task_id
            """
        )
    )
    connection.execute(
        text(
            """
            UPDATE task_evidences AS evidence
            SET assignment_id = candidate.assignment_id,
                verification_status = CASE
                    WHEN evidence.status IN ('APPROVED', 'VERIFIED') THEN 'VERIFIED'
                    ELSE 'PENDING_REVIEW'
                END
            FROM (
                SELECT task_id, MIN(id) AS assignment_id
                FROM task_assignments
                GROUP BY task_id
                HAVING COUNT(*) = 1
            ) AS candidate
            WHERE candidate.task_id = evidence.task_id
              AND evidence.assignment_id IS NULL
            """
        )
    )
    connection.execute(
        text(
            """
            UPDATE kpi_assessment_inputs
            SET self_scores_json = CASE
                    WHEN self_scores_json = '{}'::jsonb
                        THEN COALESCE(common_scores_json, '{}'::jsonb)
                    ELSE self_scores_json
                END,
                reviewed_scores_json = CASE
                    WHEN reviewed_scores_json = '{}'::jsonb
                        THEN COALESCE(common_scores_json, '{}'::jsonb)
                    ELSE reviewed_scores_json
                END,
                management_review_json = CASE
                    WHEN management_review_json = '{}'::jsonb
                        THEN COALESCE(management_metrics_json, '{}'::jsonb)
                    ELSE management_review_json
                END,
                reviewed_at = CASE
                    WHEN reviewed_by IS NOT NULL THEN COALESCE(reviewed_at, updated_at)
                    ELSE reviewed_at
                END
            """
        )
    )
    connection.execute(
        text(
            """
            UPDATE kpi_scores
            SET score_status = 'CONFIRMED',
                confirmed_at = COALESCE(confirmed_at, created_at)
            WHERE score_status = 'DRAFT'
            """
        )
    )


def upgrade() -> None:
    """Run all schema and data changes atomically with preservation checks."""

    with engine.begin() as connection:
        before_counts = _count_rows(connection)
        workflow_schema_existed = _workflow_schema_exists(connection)
        hdnd_department_existed = connection.execute(
            text("SELECT EXISTS(SELECT 1 FROM departments WHERE code = 'HDND_XA')")
        ).scalar_one()
        leadership_department_existed = connection.execute(
            text(
                "SELECT EXISTS(SELECT 1 FROM departments "
                "WHERE code IN ('LANH_DAO_HDND_UBND', 'LANH_DAO_UBND'))"
            )
        ).scalar_one()
        _assert_no_duplicate_codes(connection)
        _assert_no_orphans(connection)
        _add_columns_and_indexes(connection)
        Base.metadata.create_all(bind=connection, tables=[AuditLog.__table__])
        if not workflow_schema_existed:
            _backfill_organization(connection)
            _backfill_workflow(connection)
        _assert_no_duplicate_codes(connection)
        _assert_no_orphans(connection)

        after_counts = _count_rows(connection)
        expected_department_delta = (
            1
            if (
                not workflow_schema_existed
                and leadership_department_existed
                and not hdnd_department_existed
            )
            else 0
        )
        for table_name, before_count in before_counts.items():
            expected_count = before_count
            if table_name == "departments":
                expected_count += expected_department_delta
            if after_counts[table_name] != expected_count:
                raise RuntimeError(
                    "Migration rolled back because row count changed for "
                    f"{table_name}: expected {expected_count}, got {after_counts[table_name]}."
                )

        print("Migration 005 completed. Preserved row counts:")
        for table_name, count in after_counts.items():
            print(f"- {table_name}: {count}")


if __name__ == "__main__":
    upgrade()
