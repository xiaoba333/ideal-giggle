# -*- coding: utf-8 -*-
"""班级日志业务逻辑层。"""

from dao import classlog_dao
from dao.classlog_dao import (
    LOG_TYPES,
    MORAL_ADD,
    MORAL_DEDUCT,
    MORAL_NONE,
    MORAL_BOTH,
    display_log_type,
    participants_display,
)
from utils.date_util import format_date, parse_date, today_str


def _parse_moral_dual(
    moral_add_score=None,
    moral_add_student_ids=None,
    moral_deduct_score=None,
    moral_deduct_student_ids=None,
    **_ignored,
):
    """校验双侧德育；返回 insert/update 可用的规范化字段。"""
    from dao.classlog_dao import _normalize_moral_pair

    mtype, mscore, a_score, a_ids, d_score, d_ids = _normalize_moral_pair(
        moral_add_score,
        moral_add_student_ids,
        moral_deduct_score,
        moral_deduct_student_ids,
    )
    return {
        "moral_type": mtype,
        "moral_score": mscore,
        "moral_add_score": a_score,
        "moral_add_student_ids": a_ids,
        "moral_deduct_score": d_score,
        "moral_deduct_student_ids": d_ids,
        # 旧字段占位，避免误走 participants 自动加分
        "moral_student_ids": d_ids,
    }


def add_log(
    log_date,
    title=None,
    content=None,
    log_type=None,
    participants=None,
    type_remark=None,
    moral_type=MORAL_NONE,
    moral_score=None,
    moral_student_ids=None,
    moral_add_score=None,
    moral_add_student_ids=None,
    moral_deduct_score=None,
    moral_deduct_student_ids=None,
    image_source=None,
    clear_image=False,
    **_extra,
):
    """选择日期新增日志（含德育 / 图片附件）。"""
    log_type = (log_type or title or "").strip()
    if not log_type:
        raise ValueError("请选择日志类型")
    if log_type not in LOG_TYPES:
        raise ValueError(f"日志类型无效，应为：{' / '.join(LOG_TYPES)}")
    remark = (type_remark or "").strip() or None
    if log_type == "其他" and not remark:
        raise ValueError("选择「其他」时请填写备注")
    if log_type != "其他":
        remark = None
    date_str = format_date(log_date) if log_date else today_str()
    if not parse_date(date_str):
        raise ValueError("记录日期格式错误，应为 YYYY-MM-DD")

    # 新 UI 始终传双侧字段；旧调用仅传 moral_type 时兼容转换（不加分到「参与学生」）
    if (
        moral_add_score is None
        and moral_add_student_ids is None
        and moral_deduct_score is None
        and moral_deduct_student_ids is None
        and moral_type not in (None, MORAL_NONE)
    ):
        if moral_type == MORAL_ADD:
            moral_add_score = moral_score
            moral_add_student_ids = list(moral_student_ids or [])
        elif moral_type == MORAL_DEDUCT:
            moral_deduct_score = moral_score
            moral_deduct_student_ids = list(moral_student_ids or [])

    moral_kw = _parse_moral_dual(
        moral_add_score=moral_add_score,
        moral_add_student_ids=moral_add_student_ids or [],
        moral_deduct_score=moral_deduct_score,
        moral_deduct_student_ids=moral_deduct_student_ids or [],
    )
    image_path = ""
    if image_source and not clear_image:
        from utils.log_image_util import save_log_image
        image_path = save_log_image(image_source)
    return classlog_dao.insert_log(
        date_str,
        title=display_log_type(log_type, remark),
        content=content,
        log_type=log_type,
        participants=participants,
        type_remark=remark,
        image_path=image_path,
        **moral_kw,
    )


def edit_log(
    log_id,
    log_date,
    title=None,
    content=None,
    log_type=None,
    participants=None,
    type_remark=None,
    moral_type=MORAL_NONE,
    moral_score=None,
    moral_student_ids=None,
    moral_add_score=None,
    moral_add_student_ids=None,
    moral_deduct_score=None,
    moral_deduct_student_ids=None,
    image_source=None,
    clear_image=False,
    **_extra,
):
    """编辑日志（同步德育明细与图片）。"""
    if not log_id:
        raise ValueError("日志 id 无效")
    log_type = (log_type or title or "").strip()
    if not log_type:
        raise ValueError("请选择日志类型")
    if log_type not in LOG_TYPES:
        raise ValueError(f"日志类型无效，应为：{' / '.join(LOG_TYPES)}")
    remark = (type_remark or "").strip() or None
    if log_type == "其他" and not remark:
        raise ValueError("选择「其他」时请填写备注")
    if log_type != "其他":
        remark = None
    date_str = format_date(log_date)
    if not parse_date(date_str):
        raise ValueError("记录日期格式错误，应为 YYYY-MM-DD")

    if (
        moral_add_score is None
        and moral_add_student_ids is None
        and moral_deduct_score is None
        and moral_deduct_student_ids is None
        and moral_type not in (None, MORAL_NONE)
    ):
        if moral_type == MORAL_ADD:
            moral_add_score = moral_score
            moral_add_student_ids = list(moral_student_ids or [])
        elif moral_type == MORAL_DEDUCT:
            moral_deduct_score = moral_score
            moral_deduct_student_ids = list(moral_student_ids or [])

    moral_kw = _parse_moral_dual(
        moral_add_score=moral_add_score,
        moral_add_student_ids=moral_add_student_ids or [],
        moral_deduct_score=moral_deduct_score,
        moral_deduct_student_ids=moral_deduct_student_ids or [],
    )

    from utils.log_image_util import (
        save_log_image, delete_log_image, normalize_image_path,
    )
    old = classlog_dao.get_log_by_id(log_id) or {}
    old_path = normalize_image_path(old.get("image_path"))
    pending_delete = None
    if clear_image:
        new_path = ""
        pending_delete = old_path or None
    elif image_source:
        new_path = save_log_image(image_source)
        if old_path and old_path != new_path:
            pending_delete = old_path
    else:
        new_path = old_path

    rowcount = classlog_dao.update_log(
        log_id,
        date_str,
        title=display_log_type(log_type, remark),
        content=content,
        log_type=log_type,
        participants=participants,
        type_remark=remark,
        image_path=new_path,
        **moral_kw,
    )
    if pending_delete:
        delete_log_image(pending_delete)
    return rowcount


def remove_log(log_id):
    """删除日志（DAO 内同步清理本地图片）。"""
    if not log_id:
        raise ValueError("日志 id 无效")
    return classlog_dao.delete_log(log_id)


def get_log(log_id):
    """获取单条日志。"""
    return classlog_dao.get_log_by_id(log_id)


def list_by_date(log_date):
    """查询某日全部日志。"""
    date_str = format_date(log_date)
    if not parse_date(date_str):
        raise ValueError("记录日期格式错误，应为 YYYY-MM-DD")
    return classlog_dao.list_logs_by_date(date_str)


def search_logs(keyword=None, start_date=None, end_date=None):
    """历史日志检索。"""
    keyword = (keyword or "").strip() or None
    start_str = format_date(start_date) if start_date else None
    end_str = format_date(end_date) if end_date else None
    if start_str == "":
        start_str = None
    if end_str == "":
        end_str = None
    if start_str and not parse_date(start_str):
        raise ValueError("开始日期格式错误，应为 YYYY-MM-DD")
    if end_str and not parse_date(end_str):
        raise ValueError("结束日期格式错误，应为 YYYY-MM-DD")
    return classlog_dao.search_logs(keyword, start_str, end_str)


def list_all():
    """全部日志。"""
    return classlog_dao.list_all_logs()


def list_log_dates(start_date, end_date):
    """查询区间内有日志的日期（YYYY-MM-DD 字符串列表）。"""
    start_str = format_date(start_date)
    end_str = format_date(end_date)
    if not parse_date(start_str) or not parse_date(end_str):
        raise ValueError("日期格式错误，应为 YYYY-MM-DD")
    rows = classlog_dao.list_log_dates(start_str, end_str)
    return [format_date(r.get("log_date")) for r in rows if r.get("log_date")]


def format_participants(log_or_raw):
    """参与人员展示。"""
    if isinstance(log_or_raw, dict):
        people = log_or_raw.get("participants_list")
        if people is not None:
            if not people:
                return ""
            return "、".join(p.get("name") or f"#{p.get('id')}" for p in people)
        return participants_display(log_or_raw.get("participants"))
    return participants_display(log_or_raw)


def format_type(log):
    """日志类型展示（含其他备注）。"""
    if not isinstance(log, dict):
        return display_log_type(log)
    return display_log_type(
        log.get("log_type") or log.get("title"),
        log.get("type_remark"),
    )


def format_moral(log):
    """德育变动简要展示（支持同时加分+扣分）。"""
    if not isinstance(log, dict):
        return ""
    add_score = log.get("moral_add_score")
    deduct_score = log.get("moral_deduct_score")
    # 列表页可能没有 split 字段，回退 moral_type / moral_score
    if add_score is None and deduct_score is None:
        try:
            mtype = int(log.get("moral_type") or 0)
        except (TypeError, ValueError):
            mtype = 0
        score = log.get("moral_score")
        try:
            score = int(score) if score is not None else None
        except (TypeError, ValueError):
            score = None
        if mtype == MORAL_NONE:
            return "无变动"
        if mtype == MORAL_ADD:
            return f"加分 +{abs(score)}" if score is not None else "加分"
        if mtype == MORAL_DEDUCT:
            return f"扣分 -{abs(score)}" if score is not None else "扣分"
        if mtype == MORAL_BOTH:
            return "加分+扣分"
        return ""

    parts = []
    if add_score is not None:
        parts.append(f"加分 +{abs(int(add_score))}")
    if deduct_score is not None:
        parts.append(f"扣分 -{abs(int(deduct_score))}")
    return "；".join(parts) if parts else "无变动"
