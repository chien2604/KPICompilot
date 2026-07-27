import openpyxl
from pathlib import Path
import sys
from datetime import datetime, timedelta
import random
import unicodedata

from sqlalchemy import text

BACKEND = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND))

from db.database import SessionLocal, engine, init_extensions, Base
from core.security import hash_password
from db.models import (
    User,
    Department,
    KPITemplate,
    KPICriterion,
    DocumentTypeRule,
    KPIScore,
    Task,
    TaskAssignment,
    TaskEvidence,
    DocumentChunk,
    ChatLog,
    Report
)
from services.kpi_engine import KPIEngine
from ai_layer.rag.kuzu_graph_store import KuzuGraphStore
from ai_layer.rag.embedding_client import MockEmbeddingClient
from core.config import get_settings

LEADERSHIP_DEPT_NAME = "Lãnh đạo Sở"


def normalize_text(value):
    return unicodedata.normalize("NFC", value.strip())

def parse_excel():
    excel_path = BACKEND.parent / "Ket xuat to chuc nguoi dung_ Sở Dân tộc và Tôn giáo tỉnh Đăk Lăk.xlsx"
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    sheet = wb["taikhoan"]
    
    users_data = []
    departments_set = set()
    
    # Dữ liệu bắt đầu từ dòng 9
    for row_idx in range(9, sheet.max_row + 1):
        row = [cell.value for cell in sheet[row_idx]]
        if not row or len(row) < 7:
            continue
        
        dept_name = row[2] # Phòng ban
        full_name = row[3] # Họ và tên
        email = row[4]     # Tài khoản đăng nhập
        position = row[5]  # Chức vụ
        role_code = row[6] # Mã vai trò (leader, specialist, org_leader, org_administrator, vv)
        
        if not email or not full_name:
            continue
            
        # Clean & Normalize
        dept_name = normalize_text(dept_name)
        full_name = normalize_text(full_name)
        email = email.strip()
        position = normalize_text(position) if position else ""
        role_code = role_code.strip() if role_code else "specialist"
        
        departments_set.add(dept_name)
        users_data.append({
            "dept_name": dept_name,
            "full_name": full_name,
            "email": email,
            "position": position,
            "excel_role": role_code
        })
        
    return departments_set, users_data

def get_db_role_and_template(excel_role, position):
    """
    Map role từ Excel sang Cấu trúc DB hiện tại:
    Role DB: LEADER, MANAGER, STAFF, ADMIN
    kpi_role_template: BAN_GIAM_DOC, TRUONG_PHO_PHONG, CONG_CHUC_KHONG_CHUC_VU
    """
    er = excel_role.lower()
    pos = position.lower()
    
    if er == "org_leader" or "giám đốc" in pos or "gđ" in pos:
        return "LEADER", "BAN_GIAM_DOC"
    elif er == "leader" or "trưởng phòng" in pos or "phó trưởng phòng" in pos or "chánh văn" in pos or "phó chánh" in pos:
        return "MANAGER", "TRUONG_PHO_PHONG"
    elif er == "org_administrator" or er == "dept_administrator" or "văn thư" in pos:
        # Map văn thư hoặc admin về dạng STAFF hoặc giữ nguyên vai trò
        return "STAFF", "CONG_CHUC_KHONG_CHUC_VU"
    else:
        return "STAFF", "CONG_CHUC_KHONG_CHUC_VU"

def make_dept_code(name):
    # Viết tắt phòng ban
    name_upper = name.upper()
    if "VĂN PHÒNG" in name_upper or "VAN PHONG" in name_upper or "VĂN PHÒNG" in name_upper:
        return "VP"
    elif "CHÍNH SÁCH" in name_upper or "CHINH SACH" in name_upper:
        return "CS"
    elif "TUYÊN TRUYỀN" in name_upper or "TUYEN TRUYEN" in name_upper:
        return "TT"
    elif "TÔN GIÁO" in name_upper or "TON GIAO" in name_upper:
        return "TG"
    elif "LÃNH ĐẠO" in name_upper or "LANH DAO" in name_upper or "LÃNH ĐẠO" in name_upper:
        return "SO"
    else:
        # Lấy các chữ cái đầu
        words = name_upper.split()
        return "".join([w[0] for w in words if w])[:10]

def main():
    print("Parsing Excel...")
    depts, users_data = parse_excel()
    print(f"Parsed {len(depts)} departments and {len(users_data)} users from Excel.")
    
    db = SessionLocal()
    try:
        # 1. Clear database
        print("Clearing tables...")
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
                    kpi_criteria,
                    document_type_rules,
                    kpi_templates,
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
        
        # 1b. Seed KPI Templates & Rules
        print("Seeding KPI templates and criteria rules...")
        from services.excel_rule_loader import ROLE_TEMPLATES, DOCUMENT_RULES
        for code, spec in ROLE_TEMPLATES.items():
            template = KPITemplate(code=code, name=spec["name"], target_role=code, total_score=100)
            db.add(template)
            db.flush()
            sort_order = 1
            for group_code, group_name, max_score in spec["groups"]:
                db.add(
                    KPICriterion(
                        template_id=template.id,
                        group_code=group_code,
                        group_name=group_name,
                        criterion_code=f"{code}_{group_code}",
                        criterion_name=group_name,
                        description=f"Nhóm tiêu chí {group_name} cho {spec['name']}.",
                        calculation_rule_text="Rule Engine tính dựa trên tiến độ nhiệm vụ, hạn xử lý, loại văn bản, minh chứng và điểm tự/leader đánh giá.",
                        max_score=max_score,
                        sort_order=sort_order,
                    )
                )
                sort_order += 1
        for code, name, description, scoring in DOCUMENT_RULES:
            db.add(DocumentTypeRule(code=code, name=name, description=description, scoring_rule_text=scoring))
        db.flush()
        
        # 2. Seed Departments
        print("Seeding departments...")
        dept_mapping = {}
        # Tạo phòng ban cha Sở Dân tộc và Tôn giáo
        root_dept = Department(code="SO", name="Sở Dân tộc và Tôn giáo tỉnh Đắk Lắk", parent_id=None)
        db.add(root_dept)
        db.flush()
        dept_mapping[LEADERSHIP_DEPT_NAME] = root_dept
        
        for dept_name in depts:
            if normalize_text(dept_name) == LEADERSHIP_DEPT_NAME:
                continue
            code = make_dept_code(dept_name)
            dept_obj = Department(code=code, name=dept_name, parent_id=root_dept.id)
            db.add(dept_obj)
            db.flush()
            dept_mapping[dept_name] = dept_obj
            
        # 3. Seed Users
        print("Seeding users...")
        db_users = []
        default_hashed_pwd = hash_password("123456")
        
        for idx, u in enumerate(users_data, start=1):
            role, template = get_db_role_and_template(u["excel_role"], u["position"])
            dept = dept_mapping.get(u["dept_name"], root_dept)
            
            user = User(
                full_name=u["full_name"],
                email=u["email"],
                role=role,
                kpi_role_template=template,
                department_id=dept.id,
                position_title=u["position"],
                avatar_url=f"https://api.dicebear.com/8.x/initials/svg?seed={idx}",
                hashed_password=default_hashed_pwd,
                is_active=True
            )
            db.add(user)
            db.flush()
            db_users.append(user)
            
        print(f"Created {len(db_users)} users in database.")
        
        # 4. Seed Tasks & Assignments (Phân chia ngẫu nhiên cho users giống script cũ)
        print("Seeding tasks & assignments...")
        random.seed(42)
        statuses = ["COMPLETED"] * 158 + ["IN_PROGRESS"] * 20 + ["NOT_STARTED"] * 4 + ["OVERDUE"] * 12
        doc_types = ["A", "B", "C", "D"]
        staff_users = [u for u in db_users if u.role != "LEADER"]
        
        for index, status in enumerate(statuses, start=1):
            assignee = staff_users[(index - 1) % len(staff_users)]
            deadline_offset = random.randint(-20, 25)
            if status == "OVERDUE":
                deadline_offset = -random.randint(1, 20)
            
            task = Task(
                title=f"Nhiệm vụ {index:03d}: xử lý hồ sơ và báo cáo chuyên môn",
                description="Nhiệm vụ demo phục vụ luồng AI KPI Copilot, có hạn xử lý, loại văn bản và minh chứng kèm theo.",
                creator_id=db_users[index % 3].id,
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
            
        # 5. Seed Evidences & chunks
        print("Seeding sample evidences...")
        upload_dir = get_settings().upload_dir
        upload_dir.mkdir(parents=True, exist_ok=True)
        embedding_client = MockEmbeddingClient()
        
        tasks_for_evidence = db.query(Task).filter(Task.status.in_(["COMPLETED", "IN_PROGRESS", "OVERDUE"])).order_by(Task.id).limit(60).all()
        for index, task in enumerate(tasks_for_evidence, start=1):
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
                
        # 6. Seed KPI Scores
        print("Seeding KPI scores...")
        templates = {item.code: item.id for item in db.query(KPITemplate).all()}
        target_scores = [99, 98, 97, 96, 95, 94, 93, 92, 91, 89, 86, 86, 85, 85, 84, 84, 83, 83, 82, 82, 82, 81, 81, 80, 80, 79, 79, 78, 78, 77, 76, 75, 74, 72, 70, 68, 65, 60]
        # Nhân đôi hoặc điều chỉnh độ dài target_scores khớp với lượng users
        while len(target_scores) < len(db_users):
            target_scores.extend(target_scores.copy())
            
        engine_kpi = KPIEngine(db)
        for user, score in zip(db_users, target_scores[:len(db_users)], strict=False):
            db.add(
                KPIScore(
                    user_id=user.id,
                    period_month="2026-06",
                    template_id=templates.get(user.kpi_role_template),
                    total_score=score,
                    classification=engine_kpi.classify(score),
                    risk_level=engine_kpi.risk_level(score),
                    breakdown_json={"breakdown": [{"group_name": "Demo KPI tổng hợp", "max_score": 100, "score": score, "reasons": ["Seed demo PoC"]}]},
                    ai_explanation="Điểm demo được seed để phục vụ dashboard và chatbot lãnh đạo.",
                )
            )
            
        # 7. Seed Reports
        print("Seeding reports...")
        report_specs = [
            ("WEEKLY", "2026-W25", {"tasks_by_status": {"COMPLETED": 158, "IN_PROGRESS": 20, "NOT_STARTED": 5, "OVERDUE": 12}, "total_tasks": 195, "risk_users": [
                {"name": "Cán bộ rủi ro mẫu 1", "department": "Phòng Chính sách", "score": 62, "risk": "HIGH"},
                {"name": "Cán bộ rủi ro mẫu 2", "department": "Phòng Tôn giáo", "score": 68, "risk": "MEDIUM"},
            ]}),
            ("MONTHLY", "2026-06", {"tasks_by_status": {"COMPLETED": 158, "IN_PROGRESS": 20, "NOT_STARTED": 5, "OVERDUE": 12}, "total_tasks": 195, "risk_users": []}),
            ("WEEKLY", "2026-W24", {"tasks_by_status": {"COMPLETED": 140, "IN_PROGRESS": 18, "NOT_STARTED": 3, "OVERDUE": 8}, "total_tasks": 169, "risk_users": []}),
        ]
        for report_type, period, data in report_specs:
            completed = data['tasks_by_status']['COMPLETED']
            in_progress = data['tasks_by_status']['IN_PROGRESS']
            overdue = data['tasks_by_status']['OVERDUE']
            content_md = f"# Báo cáo {report_type} - {period}\n\n## 1. Tình hình chung\n- Tổng số nhiệm vụ: {data['total_tasks']}\n- Đã hoàn thành: {completed}\n- Đang thực hiện: {in_progress}\n- Quá hạn: {overdue}\n\n## 2. Cán bộ rủi ro cao\n"
            for ru in data.get("risk_users", []):
                content_md += f"- **{ru['name']}** ({ru['department']}): Điểm KPI {ru['score']} ({ru['risk']})\n"
                
            db.add(
                Report(
                    report_type=report_type,
                    period=period,
                    department_id=None,
                    content=content_md,
                    summary_json={"seed": True, **data},
                    created_by=db_users[0].id,
                )
            )
            
        db.commit()
        
        # 8. Sync Kuzu Graph Store
        print("Syncing Graph store...")
        try:
            graph = KuzuGraphStore(str(get_settings().kuzu_db_path))
            # clear and init graph schema if possible
            graph.init_schema()
            for department in dept_mapping.values():
                graph.upsert_department(department)
            for user in db_users:
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
            print("Graph sync completed!")
        except Exception as ge:
            print(f"Warning: Failed to sync graph: {ge}")
            
        print("[SUCCESS] Import excel to database successfully!")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Import failed: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    main()
