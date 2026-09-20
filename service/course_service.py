# -*- coding: utf-8 -*-
"""课程模式业务：笔记大类与笔记，不访问个人日记 / 随笔 / 班级日志。"""

from dao import course_dao


def list_categories():
    return course_dao.list_categories() or []


def create_category(name):
    title = (name or "").strip()
    if not title:
        raise ValueError("请填写笔记大类名称")
    if len(title) > 100:
        raise ValueError("大类名称过长")
    order = course_dao.next_category_sort()
    return course_dao.insert_category(title, order)


def rename_category(category_id, name):
    if not category_id:
        raise ValueError("笔记大类无效")
    title = (name or "").strip()
    if not title:
        raise ValueError("请填写笔记大类名称")
    if len(title) > 100:
        raise ValueError("大类名称过长")
    if not course_dao.get_category(category_id):
        raise ValueError("笔记大类不存在")
    return course_dao.update_category_name(category_id, title)


def remove_category(category_id):
    if not category_id:
        raise ValueError("笔记大类无效")
    if not course_dao.get_category(category_id):
        raise ValueError("笔记大类不存在")
    return course_dao.delete_category(category_id)


def list_notes(category_id):
    if not category_id:
        return []
    return course_dao.list_notes(category_id) or []


def get_note(note_id):
    if not note_id:
        return None
    return course_dao.get_note(note_id)


def create_note(category_id, title):
    if not category_id or not course_dao.get_category(category_id):
        raise ValueError("请先选择笔记大类")
    name = (title or "").strip()
    if not name:
        raise ValueError("请填写笔记标题")
    if len(name) > 200:
        raise ValueError("笔记标题过长")
    order = course_dao.next_note_sort(category_id)
    return course_dao.insert_note(category_id, name, order)


def rename_note(note_id, title):
    if not note_id:
        raise ValueError("笔记无效")
    name = (title or "").strip()
    if not name:
        raise ValueError("请填写笔记标题")
    if len(name) > 200:
        raise ValueError("笔记标题过长")
    if not course_dao.get_note(note_id):
        raise ValueError("笔记不存在")
    return course_dao.update_note_title(note_id, name)


def save_content(note_id, content_html, outline_json):
    if not note_id:
        raise ValueError("笔记无效")
    if not course_dao.get_note(note_id):
        raise ValueError("笔记不存在")
    return course_dao.update_note_content(
        note_id, content_html or "", outline_json or "[]"
    )


def remove_note(note_id):
    if not note_id:
        raise ValueError("笔记无效")
    if not course_dao.get_note(note_id):
        raise ValueError("笔记不存在")
    return course_dao.delete_note(note_id)
