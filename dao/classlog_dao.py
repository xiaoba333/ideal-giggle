# -*- coding: utf-8 -*-
"""班级日志表 DAO。"""

import json

from database.db_conn import execute_query, execute_one, execute_update
from dao import moral_dao

_SCHEMA_READY = False

LOG_TYPES = ("团日活动", "班会", "社会实践", "其他")

MORAL_NONE = moral_dao.MORAL_NONE
MORAL_ADD = moral_dao.MORAL_ADD
MORAL_DEDUCT = moral_dao.MORAL_DEDUCT
MORAL_BOTH = moral_dao.MORAL_BOTH


def ensure_schema():
    """补齐日志字段 + 德育列 + moral_record（幂等）。"""
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    cols = execute_query(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='class_log'"
    )
    names = {c["COLUMN_NAME"] for c in cols}
    if "log_type" not in names:
        execute_update(
            "ALTER TABLE class_log ADD COLUMN log_type VARCHAR(20) "
            "DEFAULT NULL COMMENT '日志类型' AFTER title"
        )
        execute_update(
            "UPDATE class_log SET log_type=title "
            "WHERE (log_type IS NULL OR log_type='') AND title IS NOT NULL"
        )
    if "participants" not in names:
        execute_update(
            "ALTER TABLE class_log ADD COLUMN participants TEXT "
            "DEFAULT NULL COMMENT '参与学生JSON' AFTER content"
        )
    cols = execute_query(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='class_log'"
    )
    names = {c["COLUMN_NAME"] for c in cols}
    if "type_remark" not in names:
        execute_update(
            "ALTER TABLE class_log ADD COLUMN type_remark VARCHAR(100) "
            "DEFAULT NULL COMMENT '类型为其他时的备注' AFTER log_type"
        )
    if "moral_type" not in names:
        execute_update(
            "ALTER TABLE class_log ADD COLUMN moral_type TINYINT NOT NULL "
            "DEFAULT 0 COMMENT '德育：0无变动 1加分 2扣分' AFTER participants"
        )
    if "moral_score" not in names:
        execute_update(
            "ALTER TABLE class_log ADD COLUMN moral_score INT DEFAULT NULL "
            "COMMENT '本次德育操作分数' AFTER participants"
        )
    cols = execute_query(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='class_log'"
    )
    names = {c["COLUMN_NAME"] for c in cols}
    if "image_path" not in names:
        execute_update(
            "ALTER TABLE class_log ADD COLUMN image_path VARCHAR(255) "
            "NOT NULL DEFAULT '' COMMENT '图片相对路径' AFTER participants"
        )
    moral_dao.ensure_schema()
    _SCHEMA_READY = True


def display_log_type(log_type, type_remark=None):
    """类型展示：其他时附带备注。"""
    log_type = (log_type or "").strip()
    remark = (type_remark or "").strip()
    if log_type == "其他" and remark:
        return f"其他：{remark}"
    return log_type


def dumps_participants(participants):
    """list[dict] -> JSON 字符串。"""
    if not participants:
        return None
    payload = []
    for p in participants:
        sid = p.get("id")
        name = (p.get("name") or "").strip()
        if sid is None and not name:
            continue
        item = {"name": name}
        if sid is not None:
            item["id"] = int(sid)
        payload.append(item)
    return json.dumps(payload, ensure_ascii=False) if payload else None


def loads_participants(raw):
    """JSON / 原始值 -> list[dict]。"""
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return raw
    try:
        data = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    result = []
    for p in data:
        if not isinstance(p, dict):
            continue
        name = (p.get("name") or "").strip()
        sid = p.get("id")
        item = {"name": name}
        if sid is not None:
            try:
                item["id"] = int(sid)
            except (TypeError, ValueError):
                pass
        if item.get("id") is not None or name:
            result.append(item)
    return result


def participants_display(raw):
    """参与人员展示文案。"""
    people = loads_participants(raw)
    if not people:
        return ""
    return "、".join(p.get("name") or f"#{p.get('id')}" for p in people)


def _normalize_moral_pair(add_score=None, add_ids=None, deduct_score=None, deduct_ids=None):
    """
    规范化双侧德育参数。
    返回 (moral_type, moral_score, add_score, add_ids, deduct_score, deduct_ids)
    moral_score 兼容旧字段：仅加分时为正分，仅扣分时为扣分绝对值，双侧时存加分分值。
    """
    add_ids = list(add_ids or [])
    deduct_ids = list(deduct_ids or [])

    def _as_pos_int(raw, label):
        if raw is None or str(raw).strip() == "":
            return None
        try:
            val = int(str(raw).strip())
        except (TypeError, ValueError):
            raise ValueError(f"{label}仅支持整数")
        if val == 0:
            raise ValueError(f"{label}不能为 0")
        return abs(val)

    a_score = _as_pos_int(add_score, "加分分数")
    d_score = _as_pos_int(deduct_score, "扣分分数")

    clean_add = []
    for sid in add_ids:
        try:
            clean_add.append(int(sid))
        except (TypeError, ValueError):
            continue
    clean_deduct = []
    for sid in deduct_ids:
        try:
            clean_deduct.append(int(sid))
        except (TypeError, ValueError):
            continue

    has_add = a_score is not None and bool(clean_add)
    has_deduct = d_score is not None and bool(clean_deduct)

    if a_score is not None and not clean_add:
        raise ValueError("加分请勾选需要加分的学生")
    if d_score is not None and not clean_deduct:
        raise ValueError("扣分请勾选需要扣分的学生")
    if clean_add and a_score is None:
        raise ValueError("请填写加分分数")
    if clean_deduct and d_score is None:
        raise ValueError("请填写扣分分数")

    if has_add and has_deduct:
        mtype = MORAL_BOTH
        mscore = a_score
    elif has_add:
        mtype = MORAL_ADD
        mscore = a_score
    elif has_deduct:
        mtype = MORAL_DEDUCT
        mscore = d_score
    else:
        mtype = MORAL_NONE
        mscore = None
        a_score = None
        d_score = None
        clean_add = []
        clean_deduct = []

    return mtype, mscore, a_score, clean_add, d_score, clean_deduct


def _normalize_moral(moral_type, moral_score):
    """兼容旧调用：返回 (moral_type:int, moral_score:int|None)。"""
    try:
        mtype = int(moral_type) if moral_type is not None else MORAL_NONE
    except (TypeError, ValueError):
        mtype = MORAL_NONE
    if mtype not in (MORAL_NONE, MORAL_ADD, MORAL_DEDUCT, MORAL_BOTH):
        mtype = MORAL_NONE
    if mtype == MORAL_NONE:
        return MORAL_NONE, None
    if moral_score is None or moral_score == "":
        return mtype, None
    try:
        return mtype, int(moral_score)
    except (TypeError, ValueError):
        return mtype, None


def _normalize_image_path(image_path):
    if image_path is None:
        return ""
    return str(image_path).strip().replace("\\", "/")


def _attach_participants(row):
    if row:
        row["participants_list"] = loads_participants(row.get("participants"))
        row["image_path"] = _normalize_image_path(row.get("image_path"))
        try:
            row["moral_type"] = int(row.get("moral_type") or 0)
        except (TypeError, ValueError):
            row["moral_type"] = 0
    return row


def insert_log(
    log_date,
    title,
    content=None,
    log_type=None,
    participants=None,
    type_remark=None,
    moral_type=MORAL_NONE,
    moral_score=None,
    moral_student_ids=None,
    image_path="",
    moral_add_score=None,
    moral_add_student_ids=None,
    moral_deduct_score=None,
    moral_deduct_student_ids=None,
):
    """新增班级日志（含德育），返回新记录 id。"""
    ensure_schema()
    log_type = (log_type or title or "").strip() or None
    remark = (type_remark or "").strip() or None
    if log_type != "其他":
        remark = None
    title = display_log_type(log_type, remark) or (title or "").strip()
    img = _normalize_image_path(image_path)

    mtype, mscore, a_score, a_ids, d_score, d_ids = _resolve_moral_inputs(
        moral_type=moral_type,
        moral_score=moral_score,
        moral_student_ids=moral_student_ids,
        participants=participants,
        moral_add_score=moral_add_score,
        moral_add_student_ids=moral_add_student_ids,
        moral_deduct_score=moral_deduct_score,
        moral_deduct_student_ids=moral_deduct_student_ids,
    )

    sql = (
        "INSERT INTO class_log "
        "(log_date, title, log_type, type_remark, content, participants, "
        "image_path, moral_score, moral_type) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )
    params = (
        log_date,
        title,
        log_type,
        remark,
        content,
        dumps_participants(participants),
        img,
        mscore,
        mtype,
    )
    _, last_id = execute_update(sql, params)
    _sync_moral_records(
        last_id,
        content,
        add_score=a_score,
        add_ids=a_ids,
        deduct_score=d_score,
        deduct_ids=d_ids,
    )
    return last_id


def update_log(
    log_id,
    log_date,
    title,
    content=None,
    log_type=None,
    participants=None,
    type_remark=None,
    moral_type=MORAL_NONE,
    moral_score=None,
    moral_student_ids=None,
    image_path="",
    moral_add_score=None,
    moral_add_student_ids=None,
    moral_deduct_score=None,
    moral_deduct_student_ids=None,
):
    """更新日志（同步重写德育明细），返回受影响行数。"""
    ensure_schema()
    log_type = (log_type or title or "").strip() or None
    remark = (type_remark or "").strip() or None
    if log_type != "其他":
        remark = None
    title = display_log_type(log_type, remark) or (title or "").strip()
    img = _normalize_image_path(image_path)

    mtype, mscore, a_score, a_ids, d_score, d_ids = _resolve_moral_inputs(
        moral_type=moral_type,
        moral_score=moral_score,
        moral_student_ids=moral_student_ids,
        participants=participants,
        moral_add_score=moral_add_score,
        moral_add_student_ids=moral_add_student_ids,
        moral_deduct_score=moral_deduct_score,
        moral_deduct_student_ids=moral_deduct_student_ids,
    )

    sql = (
        "UPDATE class_log SET log_date=%s, title=%s, log_type=%s, "
        "type_remark=%s, content=%s, participants=%s, image_path=%s, "
        "moral_score=%s, moral_type=%s WHERE id=%s"
    )
    params = (
        log_date,
        title,
        log_type,
        remark,
        content,
        dumps_participants(participants),
        img,
        mscore,
        mtype,
        log_id,
    )
    rowcount, _ = execute_update(sql, params)
    _sync_moral_records(
        log_id,
        content,
        add_score=a_score,
        add_ids=a_ids,
        deduct_score=d_score,
        deduct_ids=d_ids,
    )
    return rowcount


def _resolve_moral_inputs(
    moral_type=MORAL_NONE,
    moral_score=None,
    moral_student_ids=None,
    participants=None,
    moral_add_score=None,
    moral_add_student_ids=None,
    moral_deduct_score=None,
    moral_deduct_student_ids=None,
):
    """优先使用双侧新参数；否则兼容旧 moral_type / moral_score。"""
    use_new = (
        moral_add_score is not None
        or moral_add_student_ids is not None
        or moral_deduct_score is not None
        or moral_deduct_student_ids is not None
    )
    if use_new:
        return _normalize_moral_pair(
            moral_add_score,
            moral_add_student_ids or [],
            moral_deduct_score,
            moral_deduct_student_ids or [],
        )

    # 旧接口：加分仍可能传 participants（仅兼容，新 UI 不再走这里）
    mtype, mscore = _normalize_moral(moral_type, moral_score)
    if mtype == MORAL_ADD:
        a_ids = []
        for p in participants or []:
            if isinstance(p, dict) and p.get("id") is not None:
                a_ids.append(p.get("id"))
        return _normalize_moral_pair(mscore, a_ids, None, [])
    if mtype == MORAL_DEDUCT:
        return _normalize_moral_pair(None, [], mscore, moral_student_ids or [])
    if mtype == MORAL_BOTH:
        # 旧数据双侧无法从单字段还原，交由明细表；此处清空后由调用方应走新参数
        return MORAL_NONE, None, None, [], None, []
    return MORAL_NONE, None, None, [], None, []


def _sync_moral_records(
    log_id,
    reason,
    add_score=None,
    add_ids=None,
    deduct_score=None,
    deduct_ids=None,
):
    """按双侧名单重写德育明细：先删后插。"""
    moral_dao.delete_by_log_id(log_id)
    if not log_id:
        return
    if add_score is not None and add_ids:
        moral_dao.insert_records(log_id, add_ids, abs(int(add_score)), reason=reason)
    if deduct_score is not None and deduct_ids:
        moral_dao.insert_records(
            log_id, deduct_ids, -abs(int(deduct_score)), reason=reason
        )


def delete_log(log_id):
    """删除日志（moral_record 若有外键会级联；无外键则先删明细）。"""
    ensure_schema()
    row = execute_one("SELECT image_path FROM class_log WHERE id=%s", (log_id,))
    moral_dao.delete_by_log_id(log_id)
    sql = "DELETE FROM class_log WHERE id=%s"
    rowcount, _ = execute_update(sql, (log_id,))
    if rowcount and row:
        from utils.log_image_util import delete_log_image
        delete_log_image(_normalize_image_path(row.get("image_path")))
    return rowcount


def get_log_by_id(log_id):
    """按 id 查询单条日志。"""
    ensure_schema()
    sql = "SELECT * FROM class_log WHERE id=%s"
    row = execute_one(sql, (log_id,))
    row = _attach_participants(row)
    if row:
        split = moral_dao.split_records_by_sign(log_id)
        row["moral_add_score"] = split["add_score"]
        row["moral_add_student_ids"] = split["add_student_ids"]
        row["moral_deduct_score"] = split["deduct_score"]
        row["moral_deduct_student_ids"] = split["deduct_student_ids"]
        # 兼容旧字段
        row["moral_student_ids"] = list(split["deduct_student_ids"])
        row["moral_records"] = moral_dao.list_by_log_id(log_id)
    return row


def list_logs_by_date(log_date):
    """查询某日全部日志。"""
    ensure_schema()
    sql = (
        "SELECT * FROM class_log WHERE log_date=%s "
        "ORDER BY create_time DESC, id DESC"
    )
    rows = execute_query(sql, (log_date,))
    for row in rows:
        _attach_participants(row)
    return rows


def search_logs(keyword=None, start_date=None, end_date=None):
    """
    历史日志检索：关键词（类型/标题/正文/参与人）+ 日期区间。
    """
    ensure_schema()
    conditions = []
    params = []
    if keyword:
        like = f"%{keyword}%"
        conditions.append(
            "(title LIKE %s OR log_type LIKE %s OR type_remark LIKE %s "
            "OR content LIKE %s OR participants LIKE %s)"
        )
        params.extend([like, like, like, like, like])
    if start_date:
        conditions.append("log_date >= %s")
        params.append(start_date)
    if end_date:
        conditions.append("log_date <= %s")
        params.append(end_date)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = (
        f"SELECT * FROM class_log {where} "
        "ORDER BY log_date DESC, create_time DESC, id DESC"
    )
    rows = execute_query(sql, tuple(params) if params else None)
    for row in rows:
        _attach_participants(row)
    return rows


def list_all_logs():
    """查询全部日志，按日期倒序。"""
    ensure_schema()
    sql = (
        "SELECT * FROM class_log "
        "ORDER BY log_date DESC, create_time DESC, id DESC"
    )
    rows = execute_query(sql)
    for row in rows:
        _attach_participants(row)
    return rows


def list_log_dates(start_date, end_date):
    """查询区间内有日志的日期列表（去重）。"""
    ensure_schema()
    sql = (
        "SELECT DISTINCT log_date FROM class_log "
        "WHERE log_date >= %s AND log_date <= %s "
        "ORDER BY log_date ASC"
    )
    return execute_query(sql, (start_date, end_date))
