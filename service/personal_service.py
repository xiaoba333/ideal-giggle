# -*- coding: utf-8 -*-
"""个人模式业务逻辑。"""

from dao import personal_dao
from dao.personal_dao import (
    MOOD_HAPPY, MOOD_NORMAL, MOOD_TIRED, MOOD_SAD, MOOD_VALUES,
)
from utils.date_util import format_date
from utils import personal_image_util

__all__ = [
    "MOOD_HAPPY", "MOOD_NORMAL", "MOOD_TIRED", "MOOD_SAD", "MOOD_VALUES",
    "mood_display",
    "add_diary", "edit_diary", "remove_diary", "get_diary",
    "list_diaries_by_date", "list_diary_dates", "list_all_diaries",
    "add_milestone", "edit_milestone", "remove_milestone", "get_milestone",
    "list_milestones_by_date", "list_milestone_dates",
    "set_mood", "clear_mood", "get_mood", "list_mood_map",
    "calendar_marks", "wipe_personal_data",
]

_MOOD_LABELS = {
    MOOD_HAPPY: "开心",
    MOOD_NORMAL: "一般",
    MOOD_TIRED: "疲惫",
    MOOD_SAD: "沮丧",
}


def mood_display(mood):
    return _MOOD_LABELS.get(mood, "")


def add_diary(diary_date, content=None, image_source=None, clear_image=False,
              canvas_data=None):
    date_str = format_date(diary_date)
    if not date_str:
        raise ValueError("日期无效")
    content = (content or "").strip() or None
    canvas_data = canvas_data if canvas_data else None
    image_path = None
    if image_source and not clear_image:
        image_path = personal_image_util.save_personal_image(image_source)
    return personal_dao.insert_diary(date_str, content, image_path, canvas_data)


def edit_diary(diary_id, content=None, image_source=None, clear_image=False,
               canvas_data=None):
    if not diary_id:
        raise ValueError("日记 id 无效")
    old = personal_dao.get_diary_by_id(diary_id)
    if not old:
        raise ValueError("日记不存在")
    content = (content or "").strip() or None
    canvas_data = canvas_data if canvas_data else None
    old_path = old.get("image_path")
    image_path = old_path
    if clear_image:
        image_path = None
        if old_path:
            personal_image_util.delete_personal_image(old_path)
    elif image_source:
        image_path = personal_image_util.save_personal_image(image_source)
        if old_path and old_path != image_path:
            personal_image_util.delete_personal_image(old_path)
    return personal_dao.update_diary(diary_id, content, image_path, canvas_data)


def remove_diary(diary_id):
    if not diary_id:
        raise ValueError("日记 id 无效")
    old = personal_dao.get_diary_by_id(diary_id)
    rowcount = personal_dao.delete_diary(diary_id)
    if old and old.get("image_path"):
        personal_image_util.delete_personal_image(old["image_path"])
    return rowcount


def get_diary(diary_id):
    return personal_dao.get_diary_by_id(diary_id)


def list_diaries_by_date(diary_date):
    return personal_dao.list_diaries_by_date(format_date(diary_date))


def list_diary_dates(start_date=None, end_date=None):
    return [
        format_date(d)
        for d in personal_dao.list_diary_dates(
            format_date(start_date) if start_date else None,
            format_date(end_date) if end_date else None,
        )
        if format_date(d)
    ]


def list_all_diaries():
    return personal_dao.list_all_diaries()


def add_milestone(mark_date, title, content=None):
    date_str = format_date(mark_date)
    if not date_str:
        raise ValueError("日期无效")
    title = (title or "").strip()
    if not title:
        raise ValueError("里程碑标题不能为空")
    content = (content or "").strip() or None
    return personal_dao.insert_milestone(date_str, title, content)


def edit_milestone(ms_id, title, content=None):
    if not ms_id:
        raise ValueError("里程碑 id 无效")
    title = (title or "").strip()
    if not title:
        raise ValueError("里程碑标题不能为空")
    content = (content or "").strip() or None
    return personal_dao.update_milestone(ms_id, title, content)


def remove_milestone(ms_id):
    if not ms_id:
        raise ValueError("里程碑 id 无效")
    return personal_dao.delete_milestone(ms_id)


def get_milestone(ms_id):
    return personal_dao.get_milestone_by_id(ms_id)


def list_milestones_by_date(mark_date):
    return personal_dao.list_milestones_by_date(format_date(mark_date))


def list_milestone_dates(start_date=None, end_date=None):
    return [
        format_date(d)
        for d in personal_dao.list_milestone_dates(
            format_date(start_date) if start_date else None,
            format_date(end_date) if end_date else None,
        )
        if format_date(d)
    ]


def set_mood(mark_date, mood):
    date_str = format_date(mark_date)
    if not date_str:
        raise ValueError("日期无效")
    mood = (mood or "").strip()
    if mood not in MOOD_VALUES:
        raise ValueError("心情须为：开心 / 一般 / 疲惫 / 沮丧")
    return personal_dao.upsert_mood(date_str, mood)


def clear_mood(mark_date):
    date_str = format_date(mark_date)
    if not date_str:
        raise ValueError("日期无效")
    return personal_dao.delete_mood(date_str)


def get_mood(mark_date):
    row = personal_dao.get_mood(format_date(mark_date))
    return row.get("mood") if row else None


def list_mood_map(start_date=None, end_date=None):
    rows = personal_dao.list_moods_in_range(
        format_date(start_date) if start_date else None,
        format_date(end_date) if end_date else None,
    )
    result = {}
    for r in rows or []:
        key = format_date(r.get("mark_date"))
        if key:
            result[key] = r.get("mood")
    return result


def calendar_marks(start_date, end_date):
    """首页日历标记包：日记日、里程碑日、心情映射。"""
    return {
        "diary_dates": set(list_diary_dates(start_date, end_date)),
        "milestone_dates": set(list_milestone_dates(start_date, end_date)),
        "moods": list_mood_map(start_date, end_date),
    }


def wipe_personal_data():
    paths = personal_dao.wipe_all_personal_data()
    for p in paths:
        personal_image_util.delete_personal_image(p)
