# -*- coding: utf-8 -*-
"""学生业务逻辑层。"""

from dao import student_dao, settings_dao
from utils.excel_util import export_students_to_excel, import_students_from_excel


def add_student(
    student_no,
    name,
    gender=None,
    phone=None,
    moral_base=None,
    class_name=None,
):
    """新增学生；学号不能为空且不能重复。"""
    student_no = (student_no or "").strip()
    name = (name or "").strip()
    if not student_no:
        raise ValueError("学号不能为空")
    if not name:
        raise ValueError("姓名不能为空")
    exist = student_dao.get_student_by_no(student_no)
    if exist:
        raise ValueError(f"学号已存在: {student_no}")
    return student_dao.insert_student(
        student_no,
        name,
        gender,
        phone,
        moral_base=moral_base,
        class_name=class_name,
    )


def edit_student(
    student_id,
    student_no,
    name,
    gender=None,
    phone=None,
    moral_base=None,
    class_name=None,
):
    """编辑学生；校验学号唯一（排除自身）。"""
    student_no = (student_no or "").strip()
    name = (name or "").strip()
    if not student_id:
        raise ValueError("学生 id 无效")
    if not student_no:
        raise ValueError("学号不能为空")
    if not name:
        raise ValueError("姓名不能为空")
    exist = student_dao.get_student_by_no(student_no)
    if exist and exist["id"] != student_id:
        raise ValueError(f"学号已被其他学生占用: {student_no}")
    return student_dao.update_student(
        student_id,
        student_no,
        name,
        gender,
        phone,
        moral_base=moral_base,
        class_name=class_name,
    )


def remove_student(student_id):
    """删除学生。"""
    if not student_id:
        raise ValueError("学生 id 无效")
    return student_dao.delete_student(student_id)


def get_student(student_id):
    """获取单条学生。"""
    return student_dao.get_student_by_id(student_id)


def list_students(keyword=None):
    """列表或模糊搜索。"""
    keyword = (keyword or "").strip()
    if keyword:
        return student_dao.search_students(keyword)
    return student_dao.list_all_students()


def export_excel(file_path, keyword=None):
    """导出当前列表到 Excel（含班级、初始德育分）。"""
    students = list_students(keyword)
    default_class = settings_dao.get_default_class_name()
    default_base = settings_dao.get_moral_base_default()
    for s in students:
        if not (s.get("class_name") or "").strip():
            s["class_name"] = default_class
        if s.get("moral_base") is None:
            s["moral_base"] = default_base
    export_students_to_excel(students, file_path)
    return len(students)


def import_excel(file_path, skip_duplicate=True, update_existing=True):
    """
    从 Excel 导入学生（同步班级、初始德育分）。
    :param skip_duplicate: True 且 update_existing=False 时跳过已存在学号
    :param update_existing: True 时对已存在学号更新字段（含德育初始分/班级）
    :return: (success_count, skip_count, update_count, errors)
    """
    rows = import_students_from_excel(file_path)
    success_count = 0
    skip_count = 0
    update_count = 0
    errors = []
    default_base = settings_dao.get_moral_base_default()

    for row in rows:
        try:
            moral_base = row.get("moral_base")
            if moral_base is None:
                moral_base = default_base
            exist = student_dao.get_student_by_no(row["student_no"])
            if exist:
                if update_existing:
                    student_dao.update_student(
                        exist["id"],
                        row["student_no"],
                        row["name"],
                        row.get("gender"),
                        row.get("phone"),
                        moral_base=moral_base,
                        class_name=row.get("class_name"),
                    )
                    update_count += 1
                elif skip_duplicate:
                    skip_count += 1
                else:
                    raise ValueError(f"学号已存在: {row['student_no']}")
                continue
            student_dao.insert_student(
                row["student_no"],
                row["name"],
                row.get("gender"),
                row.get("phone"),
                moral_base=moral_base,
                class_name=row.get("class_name"),
            )
            success_count += 1
        except Exception as e:
            errors.append(str(e))

    return success_count, skip_count, update_count, errors
