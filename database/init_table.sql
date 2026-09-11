-- ============================================================
-- 班级管理程序 - MySQL 8.0 建表脚本
-- 使用方式：在 Navicat 中打开本文件执行
-- 字符集：utf8mb4；日期格式：YYYY-MM-DD；时间戳：DATETIME
-- ============================================================

CREATE DATABASE IF NOT EXISTS class_manager
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE class_manager;

-- ------------------------------------------------------------
-- 1. 学生信息表 student
-- ------------------------------------------------------------
DROP TABLE IF EXISTS student;
CREATE TABLE student (
    id          INT             NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    student_no  VARCHAR(32)     NOT NULL COMMENT '学号（唯一）',
    name        VARCHAR(50)     NOT NULL COMMENT '姓名',
    gender      VARCHAR(10)     DEFAULT NULL COMMENT '性别',
    phone       VARCHAR(20)     DEFAULT NULL COMMENT '联系电话',
    class_name  VARCHAR(50)     DEFAULT NULL COMMENT '班级名称',
    moral_base  INT             NOT NULL DEFAULT 100 COMMENT '个人初始德育分',
    PRIMARY KEY (id),
    UNIQUE KEY uk_student_no (student_no),
    KEY idx_student_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生信息表';

-- ------------------------------------------------------------
-- 2. 待办事项表 todo_list
-- ------------------------------------------------------------
DROP TABLE IF EXISTS todo_list;
CREATE TABLE todo_list (
    id            INT             NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    title         VARCHAR(100)    NOT NULL COMMENT '标题',
    content       TEXT            DEFAULT NULL COMMENT '详情',
    deadline      DATE            DEFAULT NULL COMMENT '截止日期 YYYY-MM-DD',
    status        TINYINT         NOT NULL DEFAULT 0 COMMENT '状态：0未完成 1已完成',
    urgency       TINYINT         NOT NULL DEFAULT 0 COMMENT '紧急度：0普通 1紧急',
    scope         TINYINT         NOT NULL DEFAULT 0 COMMENT '范围：0个人 1班级',
    complete_date DATE            DEFAULT NULL COMMENT '实际完成日期 YYYY-MM-DD',
    create_time   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    KEY idx_todo_deadline (deadline),
    KEY idx_todo_status (status),
    KEY idx_todo_urgency (urgency),
    KEY idx_todo_scope (scope),
    KEY idx_todo_status_deadline (status, deadline),
    KEY idx_todo_complete_date (complete_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='待办事项表';

-- ------------------------------------------------------------
-- 3. 班级日志表 class_log
-- ------------------------------------------------------------
DROP TABLE IF EXISTS moral_record;
DROP TABLE IF EXISTS class_log;
CREATE TABLE class_log (
    id            INT             NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    log_date      DATE            NOT NULL COMMENT '记录日期 YYYY-MM-DD',
    title         VARCHAR(100)    NOT NULL COMMENT '日志标题（与类型同步）',
    log_type      VARCHAR(20)     DEFAULT NULL COMMENT '日志类型：团日活动/班会/社会实践/其他',
    type_remark   VARCHAR(100)    DEFAULT NULL COMMENT '类型为其他时的备注',
    content       TEXT            DEFAULT NULL COMMENT '正文',
    participants  TEXT            DEFAULT NULL COMMENT '参与学生JSON：[{id,name},...]',
    image_path    VARCHAR(255)    NOT NULL DEFAULT '' COMMENT '图片相对路径（log_images/...），无图为空串',
    moral_score   INT             DEFAULT NULL COMMENT '本次德育操作分数（无变动时为空）',
    moral_type    TINYINT         NOT NULL DEFAULT 0 COMMENT '德育：0无变动 1加分 2扣分 3加扣并存',
    create_time   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    KEY idx_class_log_date (log_date),
    KEY idx_class_log_title (title),
    KEY idx_class_log_type (log_type),
    KEY idx_class_log_date_title (log_date, title),
    KEY idx_class_log_moral_type (moral_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='班级日志表';

-- ------------------------------------------------------------
-- 4. 德育变动明细表 moral_record
-- ------------------------------------------------------------
CREATE TABLE moral_record (
    id            INT             NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    student_id    INT             NOT NULL COMMENT '学生 id',
    score_change  INT             NOT NULL COMMENT '变动分数（加分为正，扣分为负）',
    change_time   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '变动时间',
    log_id        INT             DEFAULT NULL COMMENT '关联班级日志 id',
    reason        TEXT            DEFAULT NULL COMMENT '事由（复用日志内容）',
    PRIMARY KEY (id),
    KEY idx_moral_student (student_id),
    KEY idx_moral_log (log_id),
    KEY idx_moral_change_time (change_time),
    CONSTRAINT fk_moral_student FOREIGN KEY (student_id) REFERENCES student (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_moral_log FOREIGN KEY (log_id) REFERENCES class_log (id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='德育变动明细';

-- ------------------------------------------------------------
-- 5. 应用配置表 app_settings
-- ------------------------------------------------------------
DROP TABLE IF EXISTS app_settings;
CREATE TABLE app_settings (
    setting_key   VARCHAR(64)  NOT NULL COMMENT '配置键',
    setting_value VARCHAR(255) DEFAULT NULL COMMENT '配置值',
    PRIMARY KEY (setting_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='应用配置';

INSERT INTO app_settings (setting_key, setting_value) VALUES
    ('moral_base_default', '100'),
    ('default_class_name', '软件工程2506班');

-- ------------------------------------------------------------
-- 6. 个人模式：日记 / 里程碑 / 心情（与班级业务隔离）
-- ------------------------------------------------------------
DROP TABLE IF EXISTS personal_diary;
CREATE TABLE personal_diary (
    id          INT             NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    diary_date  DATE            NOT NULL COMMENT '日记日期',
    content     TEXT            DEFAULT NULL COMMENT '正文摘要',
    canvas_data MEDIUMTEXT      DEFAULT NULL COMMENT '混合画布JSON(文字+手绘)',
    image_path  VARCHAR(255)    DEFAULT NULL COMMENT '配图相对路径',
    create_time DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_personal_diary_date (diary_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='个人日记';

DROP TABLE IF EXISTS personal_milestone;
CREATE TABLE personal_milestone (
    id          INT             NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    mark_date   DATE            NOT NULL COMMENT '里程碑日期',
    title       VARCHAR(100)    NOT NULL COMMENT '标题',
    content     TEXT            DEFAULT NULL COMMENT '详情',
    create_time DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_personal_ms_date (mark_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='个人里程碑';

DROP TABLE IF EXISTS personal_mood;
CREATE TABLE personal_mood (
    mark_date   DATE            NOT NULL COMMENT '日期',
    mood        VARCHAR(16)     NOT NULL COMMENT '心情标签',
    update_time DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (mark_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='个人心情';

-- ------------------------------------------------------------
-- 7. 感触随笔：黑板 / 便签（独立于日历日记）
-- ------------------------------------------------------------
DROP TABLE IF EXISTS personal_sticky_note;
DROP TABLE IF EXISTS personal_blackboard;
CREATE TABLE personal_blackboard (
    id          INT             NOT NULL AUTO_INCREMENT COMMENT '黑板ID',
    title       VARCHAR(100)    NOT NULL DEFAULT '黑板' COMMENT '标题',
    sort_order  INT             NOT NULL DEFAULT 0 COMMENT '排序',
    create_time DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_board_sort (sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='感触随笔黑板';

CREATE TABLE personal_sticky_note (
    id          INT             NOT NULL AUTO_INCREMENT COMMENT '便签ID',
    board_id    INT             NOT NULL COMMENT '归属黑板ID',
    pos_x       INT             NOT NULL DEFAULT 40 COMMENT 'X坐标',
    pos_y       INT             NOT NULL DEFAULT 40 COMMENT 'Y坐标',
    width       INT             NOT NULL DEFAULT 118 COMMENT '宽度',
    height      INT             NOT NULL DEFAULT 108 COMMENT '高度',
    rotation    DOUBLE          NOT NULL DEFAULT 0 COMMENT '倾斜角度',
    content     TEXT            DEFAULT NULL COMMENT '完整文本',
    bg_color    VARCHAR(16)     NOT NULL DEFAULT '#f3e6c8' COMMENT '底色',
    z_order     INT             NOT NULL DEFAULT 0 COMMENT '叠放层级',
    create_time DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_note_board (board_id),
    CONSTRAINT fk_note_board FOREIGN KEY (board_id)
        REFERENCES personal_blackboard (id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='感触随笔便签';
