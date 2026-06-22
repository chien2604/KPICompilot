from datetime import datetime, timedelta
from pathlib import Path
import random
import sys

from sqlalchemy import text

BACKEND = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND))

from ai_layer.rag.kuzu_graph_store import KuzuGraphStore  # noqa: E402
from ai_layer.rag.embedding_client import MockEmbeddingClient  # noqa: E402
from xoa.report_block_builder import build_fallback_blocks  # noqa: E402
from xoa.report_html_renderer import render_fragment  # noqa: E402
from core.config import get_settings  # noqa: E402
from db.database import SessionLocal  # noqa: E402
from db.models import (  # noqa: E402
    ChatLog,
    Department,
    DocumentChunk,
    KPIScore,
    KPITemplate,
    Report,
    Task,
    TaskAssignment,
    TaskEvidence,
    User,
)
from services.kpi_engine import KPIEngine  # noqa: E402


DEPARTMENTS = [
    ("SO", "Sở Dân tộc - Tôn giáo", None),
    ("VP", "Văn phòng Sở", "SO"),
    ("DT", "Phòng Dân tộc", "SO"),
    ("TG", "Phòng Tôn giáo", "SO"),
    ("TT", "Thanh tra", "SO"),
]


def main() -> None:
    db = SessionLocal()
    try:
        _clear(db)
        departments = _seed_departments(db)
        users = _seed_users(db, departments)
        _seed_tasks(db, users, departments)
        _seed_sample_evidences(db, users)
        _seed_kpi_scores(db, users)
        _seed_chat_logs_and_reports(db, users)
        _sync_graph(db, users, departments)
        db.commit()
    finally:
        db.close()


def _clear(db) -> None:
    db.execute(
        text(
            """
            TRUNCATE TABLE
                conversation_summary,
                messages,
                conversations,
                chat_logs,
                reports,
                kpi_scores,
                document_chunks,
                task_evidences,
                task_assignments,
                tasks,
                users,
                departments
            RESTART IDENTITY CASCADE
            """
        )
    )
    db.commit()


def _seed_departments(db) -> dict[str, Department]:
    rows: dict[str, Department] = {}
    for code, name, parent_code in DEPARTMENTS:
        parent = rows.get(parent_code)
        item = Department(code=code, name=name, parent_id=parent.id if parent else None)
        db.add(item)
        db.flush()
        rows[code] = item
    return rows


def _seed_users(db, departments: dict[str, Department]) -> list[User]:
    users: list[User] = []
    specs = [
        ("Nguyễn Minh An", "LEADER", "BAN_GIAM_DOC", departments["SO"], "Giám đốc Sở"),
        ("Trần Thu Hà", "LEADER", "BAN_GIAM_DOC", departments["SO"], "Phó Giám đốc Sở"),
        ("Phạm Quốc Bảo", "LEADER", "BAN_GIAM_DOC", departments["SO"], "Phó Giám đốc Sở"),
    ]
    for dep_code, manager_name in [("VP", "Lê Thị Mai"), ("DT", "Hoàng Văn Nam"), ("TG", "Vũ Thanh Hương"), ("TT", "Đỗ Quang Huy")]:
        specs.append((manager_name, "MANAGER", "TRUONG_PHO_PHONG", departments[dep_code], "Trưởng phòng"))
        specs.append((f"Phó {manager_name.split()[-1]}", "MANAGER", "TRUONG_PHO_PHONG", departments[dep_code], "Phó trưởng phòng"))
    base_names = [
        "Nguyễn Lan Anh", "Trần Đức Anh", "Phạm Ngọc Ánh", "Lê Gia Bảo", "Hoàng Minh Châu", "Vũ Hải Đăng",
        "Đỗ Thùy Dương", "Bùi Phương Giang", "Ngô Minh Hiếu", "Dương Khánh Linh", "Mai Quang Long", "Tạ Kim Ngân",
        "Cao Nhật Minh", "Phan Thảo My", "Lý Tuấn Phong", "Đinh Hồng Quân", "Hà Việt Sơn", "Tô Bảo Trâm",
        "Chu Minh Tú", "La Hoài Vân", "Triệu Hải Yến", "Kiều Đức Toàn", "Mạc Thu Trang", "Ninh Phúc Khang",
        "Quách Anh Khoa", "Đặng Hữu Lâm", "Đoàn Diễm My",
    ]
    dep_cycle = [departments["VP"], departments["DT"], departments["TG"], departments["TT"]]
    for index, name in enumerate(base_names):
        specs.append((name, "STAFF", "CONG_CHUC_KHONG_CHUC_VU", dep_cycle[index % len(dep_cycle)], "Chuyên viên"))
    for index, (name, role, template, department, position) in enumerate(specs[:38], start=1):
        user = User(
            full_name=name,
            email=f"user{index}@demo.local",
            role=role,
            kpi_role_template=template,
            department_id=department.id,
            position_title=position,
            avatar_url=f"https://api.dicebear.com/8.x/initials/svg?seed={index}",
            is_active=True,
        )
        db.add(user)
        users.append(user)
    db.flush()
    return users


def _seed_tasks(db, users: list[User], departments: dict[str, Department]) -> None:
    random.seed(42)
    statuses = ["COMPLETED"] * 158 + ["IN_PROGRESS"] * 20 + ["NOT_STARTED"] * 4 + ["OVERDUE"] * 12
    doc_types = ["A", "B", "C", "D"]
    staff = [u for u in users if u.role != "LEADER"]
    for index, status in enumerate(statuses, start=1):
        assignee = staff[(index - 1) % len(staff)]
        deadline_offset = random.randint(-20, 25)
        if status == "OVERDUE":
            deadline_offset = -random.randint(1, 20)
        task = Task(
            title=f"Nhiệm vụ {index:03d}: xử lý hồ sơ và báo cáo chuyên môn",
            description="Nhiệm vụ demo phục vụ luồng AI KPI Copilot, có hạn xử lý, loại văn bản và minh chứng kèm theo.",
            creator_id=users[index % 3].id,
            department_id=assignee.department_id,
            deadline=datetime.utcnow() + timedelta(days=deadline_offset),
            weight=random.choice([0.8, 1.0, 1.2, 1.5]),
            document_type=random.choice(doc_types),
            status=status,
            priority=random.choice(["LOW", "MEDIUM", "HIGH"]),
        )
        db.add(task)
        db.flush()
        progress = {"COMPLETED": 100, "IN_PROGRESS": random.randint(45, 85), "NOT_STARTED": 0, "OVERDUE": random.randint(35, 75)}[status]
        db.add(TaskAssignment(task_id=task.id, user_id=assignee.id, progress_percent=progress, self_score=min(100, progress + 5)))
    db.flush()


def _seed_sample_evidences(db, users: list[User]) -> None:
    upload_dir = get_settings().upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    embedding_client = MockEmbeddingClient()
    tasks = db.query(Task).filter(Task.status.in_(["COMPLETED", "IN_PROGRESS", "OVERDUE"])).order_by(Task.id).limit(60).all()
    for index, task in enumerate(tasks, start=1):
        path = upload_dir / f"sample_evidence_{index}.txt"
        status_note = {
            "COMPLETED": "đã hoàn thành đúng hạn, có kết quả nghiệm thu và gửi lãnh đạo phê duyệt",
            "IN_PROGRESS": "đang thực hiện, đã có bản dự thảo và còn chờ góp ý của đơn vị phối hợp",
            "OVERDUE": "chậm tiến độ do thiếu hồ sơ đầu vào, cần bổ sung tài liệu và gia hạn xử lý",
        }.get(task.status, "đã cập nhật tiến độ")
        path.write_text(
            (
                f"Minh chứng nhiệm vụ {task.id}: {task.title}. Trạng thái: {task.status}. "
                f"Nội dung xử lý: {status_note}. Nhóm văn bản {task.document_type}. "
                "Tài liệu gồm biên bản xử lý, bảng tổng hợp kết quả, ý kiến phối hợp và kiến nghị tiếp theo."
            ),
            encoding="utf-8",
        )
        assignment = task.assignments[0]
        relevance = max(45, min(96, {"COMPLETED": 86, "IN_PROGRESS": 72, "OVERDUE": 58}.get(task.status, 65) + index % 8))
        evidence = TaskEvidence(
            task_id=task.id,
            uploaded_by=assignment.user_id,
            file_name=path.name,
            file_type="text/plain",
            file_path=str(path),
            extracted_text=path.read_text(encoding="utf-8"),
            ai_relevance_score=relevance,
            ai_summary="Minh chứng thể hiện tình trạng xử lý nhiệm vụ, kết quả chính và các điểm cần theo dõi.",
            ai_missing_points='["Bổ sung số văn bản phê duyệt nếu có", "Cập nhật người chịu trách nhiệm bước tiếp theo"]' if task.status != "COMPLETED" else "[]",
            status="ANALYZED",
        )
        db.add(evidence)
        db.flush()
        chunks = [
            evidence.extracted_text[:700],
            f"Ngữ cảnh KPI: nhiệm vụ {task.id}, cán bộ {assignment.user_id}, trạng thái {task.status}, độ phù hợp minh chứng {relevance}.",
        ]
        embeddings = embedding_client.embed_texts(chunks)
        for chunk_index, (content, embedding) in enumerate(zip(chunks, embeddings, strict=False)):
            db.add(
                DocumentChunk(
                    evidence_id=evidence.id,
                    task_id=task.id,
                    chunk_index=chunk_index,
                    content=content,
                    embedding=embedding,
                    metadata_json={"seed": True, "task_status": task.status, "document_type": task.document_type},
                )
            )
    db.flush()


def _seed_kpi_scores(db, users: list[User]) -> None:
    templates = {item.code: item.id for item in db.query(KPITemplate).all()}
    target_scores = [99, 98, 97, 96, 95, 94, 93, 92, 91, 89, 86, 86, 85, 85, 84, 84, 83, 83, 82, 82, 82, 81, 81, 80, 80, 79, 79, 78, 78, 77, 76, 75, 74, 72, 70, 68, 65, 60]
    engine = KPIEngine(db)
    for user, score in zip(users, target_scores, strict=False):
        db.add(
            KPIScore(
                user_id=user.id,
                period_month="2026-06",
                template_id=templates.get(user.kpi_role_template),
                total_score=score,
                classification=engine.classify(score),
                risk_level=engine.risk_level(score),
                breakdown_json={"breakdown": [{"group_name": "Demo KPI tổng hợp", "max_score": 100, "score": score, "reasons": ["Seed demo PoC"]}]},
                ai_explanation="Điểm demo được seed để phục vụ dashboard và chatbot lãnh đạo.",
            )
        )
    db.flush()


def _seed_chat_logs_and_reports(db, users: list[User]) -> None:
    questions = [
        ("Ai có nguy cơ không đạt KPI?", "KPI_RISK_USERS", "Nhóm rủi ro cao tập trung ở các cán bộ có điểm dưới 70 và nhiệm vụ quá hạn."),
        ("Phòng nào đang chậm tiến độ?", "SLOW_DEPARTMENTS", "Các phòng có nhiệm vụ quá hạn cần được ưu tiên rà soát trong giao ban tuần."),
        ("Vì sao cán bộ điểm thấp?", "EMPLOYEE_PROFILE", "Nguyên nhân chính thường là tiến độ thấp, nhiệm vụ quá hạn và minh chứng chưa đủ rõ."),
        ("Sinh báo cáo giao ban tuần này.", "GENERATE_REPORT", "Đã tổng hợp tình hình KPI, nhiệm vụ chậm và kiến nghị xử lý."),
    ]
    for index, (question, intent, answer) in enumerate(questions, start=1):
        db.add(
            ChatLog(
                user_id=users[index % len(users)].id,
                question=question,
                intent=intent,
                answer=answer,
                sources_json=[{"type": "seed", "note": "Dữ liệu hội thoại mẫu"}],
            )
        )

    # Báo cáo seed: dùng report_data (blocks) làm nguồn dữ liệu chính,
    # content (HTML) được render lại từ report_data để đảm bảo đồng bộ.
    report_specs = [
        ("WEEKLY", "2026-W25", {"tasks_by_status": {"COMPLETED": 158, "IN_PROGRESS": 20, "NOT_STARTED": 5, "OVERDUE": 12}, "total_tasks": 195, "risk_users": [
            {"name": "Cán bộ rủi ro mẫu 1", "department": "Phòng Dân tộc", "score": 62, "risk": "HIGH"},
            {"name": "Cán bộ rủi ro mẫu 2", "department": "Phòng Tôn giáo", "score": 68, "risk": "MEDIUM"},
        ]}),
        ("MONTHLY", "2026-06", {"tasks_by_status": {"COMPLETED": 158, "IN_PROGRESS": 20, "NOT_STARTED": 5, "OVERDUE": 12}, "total_tasks": 195, "risk_users": []}),
        ("WEEKLY", "2026-W24", {"tasks_by_status": {"COMPLETED": 140, "IN_PROGRESS": 18, "NOT_STARTED": 3, "OVERDUE": 8}, "total_tasks": 169, "risk_users": []}),
    ]
    for report_type, period, data in report_specs:
        report_data = build_fallback_blocks(data, report_type, period)
        db.add(
            Report(
                report_type=report_type,
                period=period,
                department_id=None,
                report_data=report_data,
                content=render_fragment(report_data),
                summary_json={"seed": True, **data},
                created_by=users[0].id,
            )
        )
    db.flush()


def _sync_graph(db, users: list[User], departments: dict[str, Department]) -> None:
    graph = KuzuGraphStore(str(get_settings().kuzu_db_path))
    graph.init_schema()
    for department in departments.values():
        graph.upsert_department(department)
    for user in users:
        graph.upsert_user(user)
        if user.department_id:
            graph.link_user_department(user.id, user.department_id)
    for task in db.query(Task).limit(80).all():
        graph.upsert_task(task)
        for assignment in task.assignments:
            graph.link_user_task(assignment.user_id, task.id)
        for evidence in task.evidences:
            graph.upsert_evidence(evidence)
            graph.link_task_evidence(task.id, evidence.id)
            for chunk in db.query(DocumentChunk).filter(DocumentChunk.evidence_id == evidence.id).all():
                graph.upsert_chunk(chunk)
                graph.link_evidence_chunk(evidence.id, chunk.id)


if __name__ == "__main__":
    main()