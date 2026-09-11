# -*- coding: utf-8 -*-
"""感触随笔业务逻辑（与日记/日历隔离）。"""

from dao import essay_dao

DEFAULT_NOTE_BG = essay_dao.DEFAULT_NOTE_BG


def list_boards():
    return essay_dao.list_boards() or []


def ensure_at_least_one_board():
    boards = list_boards()
    if boards:
        return boards
    essay_dao.insert_board("未命名", 0)
    return list_boards()


def create_board(title=None):
    order = essay_dao.next_board_sort()
    name = (title or "").strip()
    if not name:
        raise ValueError("请填写黑板名称")
    return essay_dao.insert_board(name, order)


def rename_board(board_id, title):
    if not board_id:
        raise ValueError("黑板无效")
    name = (title or "").strip()
    if not name:
        raise ValueError("请填写黑板名称")
    return essay_dao.update_board_title(board_id, name)


def remove_board(board_id):
    boards = list_boards()
    if len(boards) <= 1:
        raise ValueError("至少保留一块黑板")
    return essay_dao.delete_board(board_id)


def list_notes(board_id):
    if not board_id:
        return []
    return essay_dao.list_notes_by_board(board_id) or []


def add_note(board_id, content, pos_x=48, pos_y=48, bg_color=None,
             width=118, height=108, rotation=None):
    if not board_id:
        raise ValueError("黑板无效")
    text = (content or "").strip()
    if not text:
        raise ValueError("便签内容不能为空")
    import random
    if rotation is None:
        rotation = random.uniform(-10, 10)
    z = essay_dao.max_z_order(board_id) + 1
    return essay_dao.insert_note(
        board_id,
        pos_x=int(pos_x),
        pos_y=int(pos_y),
        content=text,
        bg_color=bg_color or DEFAULT_NOTE_BG,
        z_order=z,
        width=int(width),
        height=int(height),
        rotation=float(rotation),
    )


def edit_note(note_id, content=None, pos_x=None, pos_y=None, z_order=None,
              width=None, height=None, rotation=None):
    if not note_id:
        raise ValueError("便签无效")
    if content is not None:
        content = content.strip()
        if not content:
            raise ValueError("便签内容不能为空")
    return essay_dao.update_note(
        note_id, content=content, pos_x=pos_x, pos_y=pos_y, z_order=z_order,
        width=width, height=height, rotation=rotation,
    )


def move_note(note_id, pos_x, pos_y, raise_z=True):
    if not note_id:
        raise ValueError("便签无效")
    note = essay_dao.get_note(note_id)
    if not note:
        raise ValueError("便签不存在")
    z = None
    if raise_z:
        z = essay_dao.max_z_order(note["board_id"]) + 1
    return essay_dao.update_note(note_id, pos_x=int(pos_x), pos_y=int(pos_y), z_order=z)


def resize_note(note_id, width, height, raise_z=True):
    if not note_id:
        raise ValueError("便签无效")
    note = essay_dao.get_note(note_id)
    if not note:
        raise ValueError("便签不存在")
    z = None
    if raise_z:
        z = essay_dao.max_z_order(note["board_id"]) + 1
    return essay_dao.update_note(
        note_id, width=int(width), height=int(height), z_order=z
    )


def rotate_note(note_id, rotation, raise_z=True):
    if not note_id:
        raise ValueError("便签无效")
    note = essay_dao.get_note(note_id)
    if not note:
        raise ValueError("便签不存在")
    z = None
    if raise_z:
        z = essay_dao.max_z_order(note["board_id"]) + 1
    return essay_dao.update_note(
        note_id, rotation=float(rotation), z_order=z
    )


def transfer_note(note_id, target_board_id, pos_x=48, pos_y=48):
    """将便签移到另一块黑板。"""
    if not note_id:
        raise ValueError("便签无效")
    if not target_board_id:
        raise ValueError("目标黑板无效")
    note = essay_dao.get_note(note_id)
    if not note:
        raise ValueError("便签不存在")
    board = essay_dao.get_board(target_board_id)
    if not board:
        raise ValueError("目标黑板不存在")
    if int(note["board_id"]) == int(target_board_id):
        return essay_dao.update_note(
            note_id, pos_x=int(pos_x), pos_y=int(pos_y)
        )
    z = essay_dao.max_z_order(target_board_id) + 1
    return essay_dao.update_note(
        note_id,
        board_id=int(target_board_id),
        pos_x=int(pos_x),
        pos_y=int(pos_y),
        z_order=z,
    )


def remove_note(note_id):
    if not note_id:
        raise ValueError("便签无效")
    return essay_dao.delete_note(note_id)


def get_note(note_id):
    return essay_dao.get_note(note_id)
