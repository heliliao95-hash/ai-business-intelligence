
import hashlib
import hmac
import secrets
import sqlite3
from pathlib import Path
from datetime import datetime, date

import pandas as pd
import streamlit as st

DB_FILE = Path(__file__).resolve().parent / "users.db"


def get_connection():
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        310000
    ).hex()

    return salt, password_hash


def verify_password(password, salt, password_hash):
    _, calculated_hash = hash_password(password, salt)
    return hmac.compare_digest(calculated_hash, password_hash)


def log_event(username, action, detail=""):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO audit_logs (username, action, detail, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (username, action, detail, current_time())
        )


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                action TEXT NOT NULL,
                detail TEXT,
                created_at TEXT NOT NULL
            )
        """)

        admin_username = str(st.secrets["auth"]["username"])
        admin_password = str(st.secrets["auth"]["password"])

        existing_admin = connection.execute(
            "SELECT username FROM users WHERE username = ?",
            (admin_username,)
        ).fetchone()

        if existing_admin is None:
            salt, password_hash = hash_password(admin_password)

            connection.execute(
                """
                INSERT INTO users
                (username, salt, password_hash, role, enabled, created_at)
                VALUES (?, ?, ?, 'admin', 1, ?)
                """,
                (
                    admin_username,
                    salt,
                    password_hash,
                    current_time()
                )
            )


def authenticate(username, password):
    with get_connection() as connection:
        user = connection.execute(
            """
            SELECT username, salt, password_hash, role, enabled
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

    if user is None or user["enabled"] != 1:
        return False

    if not verify_password(
        password,
        user["salt"],
        user["password_hash"]
    ):
        return False

    st.session_state["authenticated"] = True
    st.session_state["username"] = user["username"]
    st.session_state["role"] = user["role"]

    log_event(username, "登录成功", "用户登录系统")

    return True


def create_user(username, password):
    username = username.strip()

    if len(username) < 3:
        return False, "账号至少需要 3 个字符"

    if len(password) < 8:
        return False, "密码至少需要 8 个字符"

    salt, password_hash = hash_password(password)

    try:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO users
                (username, salt, password_hash, role, enabled, created_at)
                VALUES (?, ?, ?, 'user', 1, ?)
                """,
                (
                    username,
                    salt,
                    password_hash,
                    current_time()
                )
            )

        log_event(
            st.session_state.get("username", "unknown"),
            "创建用户",
            f"创建账号：{username}"
        )

        return True, "用户创建成功"

    except sqlite3.IntegrityError:
        return False, "该账号已经存在"


def get_users():
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT username, role, enabled, created_at
            FROM users
            ORDER BY role, username
            """
        ).fetchall()


def update_user_status(username, enabled):
    if username == st.session_state.get("username") and not enabled:
        return False, "不能禁用当前登录的管理员账号"

    with get_connection() as connection:
        connection.execute(
            "UPDATE users SET enabled = ? WHERE username = ?",
            (1 if enabled else 0, username)
        )

    action = "启用用户" if enabled else "禁用用户"

    log_event(
        st.session_state.get("username", "unknown"),
        action,
        f"操作账号：{username}"
    )

    return True, "账号状态更新成功"


def reset_user_password(username, new_password):
    if len(new_password) < 8:
        return False, "密码至少需要 8 个字符"

    salt, password_hash = hash_password(new_password)

    with get_connection() as connection:
        result = connection.execute(
            """
            UPDATE users
            SET salt = ?, password_hash = ?
            WHERE username = ?
            """,
            (salt, password_hash, username)
        )

    if result.rowcount == 0:
        return False, "用户不存在"

    log_event(
        st.session_state.get("username", "unknown"),
        "重置密码",
        f"重置账号：{username}"
    )

    return True, "密码重置成功"


def change_own_password(old_password, new_password, confirm_password):
    username = st.session_state.get("username")

    if not username:
        return False, "登录状态无效，请重新登录"

    if len(new_password) < 8:
        return False, "新密码至少需要 8 个字符"

    if new_password != confirm_password:
        return False, "两次输入的新密码不一致"

    if old_password == new_password:
        return False, "新密码不能与旧密码相同"

    with get_connection() as connection:
        user = connection.execute(
            """
            SELECT salt, password_hash
            FROM users
            WHERE username = ? AND enabled = 1
            """,
            (username,)
        ).fetchone()

        if user is None:
            return False, "用户不存在或账号已禁用"

        if not verify_password(
            old_password,
            user["salt"],
            user["password_hash"]
        ):
            log_event(username, "修改密码失败", "旧密码验证失败")
            return False, "旧密码不正确"

        salt, password_hash = hash_password(new_password)

        connection.execute(
            """
            UPDATE users
            SET salt = ?, password_hash = ?
            WHERE username = ?
            """,
            (salt, password_hash, username)
        )

    log_event(username, "修改密码", "用户自主修改密码")

    return True, "密码修改成功"


def get_audit_logs(limit=500):
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT id, username, action, detail, created_at
            FROM audit_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()


def render_admin_dashboard():
    if st.session_state.get("role") != "admin":
        return

    users = get_users()
    logs = get_audit_logs(1000)

    today = date.today().isoformat()

    total_users = len(users)
    enabled_users = sum(user["enabled"] == 1 for user in users)
    disabled_users = total_users - enabled_users

    today_logs = [
        item for item in logs
        if str(item["created_at"]).startswith(today)
    ]

    today_logins = sum(
        item["action"] == "登录成功"
        for item in today_logs
    )

    st.title("🛡️ 系统管理中心")
    st.caption("管理员专属运营仪表盘")

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("用户总数", total_users)
    c2.metric("启用用户", enabled_users)
    c3.metric("禁用用户", disabled_users)
    c4.metric("今日登录次数", today_logins)
    c5.metric("今日操作次数", len(today_logs))

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("用户账号分布")

        role_counts = pd.DataFrame([
            {
                "角色": "管理员",
                "数量": sum(user["role"] == "admin" for user in users)
            },
            {
                "角色": "普通用户",
                "数量": sum(user["role"] == "user" for user in users)
            }
        ])

        st.bar_chart(
            role_counts.set_index("角色"),
            y="数量"
        )

    with right:
        st.subheader("账号状态分布")

        status_counts = pd.DataFrame([
            {
                "状态": "启用",
                "数量": enabled_users
            },
            {
                "状态": "禁用",
                "数量": disabled_users
            }
        ])

        st.bar_chart(
            status_counts.set_index("状态"),
            y="数量"
        )

    st.divider()

    st.subheader("最近注册用户")

    recent_users = sorted(
        users,
        key=lambda user: user["created_at"],
        reverse=True
    )[:10]

    if recent_users:
        recent_user_data = [
            {
                "账号": user["username"],
                "角色": user["role"],
                "状态": "启用" if user["enabled"] else "禁用",
                "注册时间": user["created_at"]
            }
            for user in recent_users
        ]

        st.dataframe(
            recent_user_data,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("暂无注册用户")

    st.divider()

    st.subheader("最近系统操作")

    recent_logs = logs[:20]

    if recent_logs:
        recent_log_data = [
            {
                "操作账号": item["username"],
                "操作类型": item["action"],
                "操作详情": item["detail"],
                "操作时间": item["created_at"]
            }
            for item in recent_logs
        ]

        st.dataframe(
            recent_log_data,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("暂无系统操作记录")

    st.divider()

    if logs:
        log_df = pd.DataFrame([
            {
                "操作账号": item["username"],
                "操作类型": item["action"],
                "操作详情": item["detail"],
                "操作时间": item["created_at"]
            }
            for item in logs
        ])

        st.download_button(
            "下载系统操作日志 CSV",
            data=log_df.to_csv(
                index=False,
                encoding="utf-8-sig"
            ),
            file_name="system_audit_logs.csv",
            mime="text/csv"
        )


def render_password_panel():
    with st.sidebar.expander("🔑 修改我的密码", expanded=False):
        with st.form("change_own_password_form"):
            old_password = st.text_input(
                "当前密码",
                type="password"
            )

            new_password = st.text_input(
                "新密码",
                type="password"
            )

            confirm_password = st.text_input(
                "确认新密码",
                type="password"
            )

            submitted = st.form_submit_button(
                "确认修改密码",
                use_container_width=True
            )

        if submitted:
            success, message = change_own_password(
                old_password,
                new_password,
                confirm_password
            )

            if success:
                st.success(message)
            else:
                st.error(message)


def render_audit_panel():
    if st.session_state.get("role") != "admin":
        return

    with st.sidebar.expander("📋 系统操作日志", expanded=False):
        logs = get_audit_logs()

        st.caption(f"最近 {len(logs)} 条操作记录")

        if logs:
            log_data = [
                {
                    "操作账号": item["username"],
                    "操作类型": item["action"],
                    "操作详情": item["detail"],
                    "操作时间": item["created_at"]
                }
                for item in logs
            ]

            log_df = pd.DataFrame(log_data)

            st.dataframe(
                log_df,
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                "下载操作日志 CSV",
                data=log_df.to_csv(
                    index=False,
                    encoding="utf-8-sig"
                ),
                file_name="system_audit_logs.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("暂无操作记录")


def render_admin_panel():
    if st.session_state.get("role") != "admin":
        return

    with st.sidebar.expander("👥 用户管理", expanded=False):
        st.subheader("创建用户")

        with st.form("create_user_form"):
            new_username = st.text_input("新用户账号")
            new_password = st.text_input(
                "初始密码",
                type="password"
            )

            create_submitted = st.form_submit_button(
                "创建用户",
                use_container_width=True
            )

        if create_submitted:
            success, message = create_user(
                new_username,
                new_password
            )

            if success:
                st.success(message)
            else:
                st.error(message)

        st.divider()
        st.subheader("账号列表")

        users = get_users()

        if users:
            display_users = [
                {
                    "账号": user["username"],
                    "角色": user["role"],
                    "状态": "启用" if user["enabled"] else "禁用",
                    "创建时间": user["created_at"]
                }
                for user in users
            ]

            st.dataframe(
                display_users,
                use_container_width=True,
                hide_index=True
            )

        manageable_users = [
            user["username"]
            for user in users
            if user["username"] != st.session_state.get("username")
        ]

        if manageable_users:
            st.divider()
            st.subheader("账号操作")

            selected_user = st.selectbox(
                "选择用户",
                manageable_users,
                key="manage_selected_user"
            )

            selected_record = next(
                user for user in users
                if user["username"] == selected_user
            )

            if selected_record["role"] == "admin":
                st.warning("其他管理员账号暂不支持在此页面操作。")
            else:
                if selected_record["enabled"]:
                    if st.button(
                        "禁用该账号",
                        use_container_width=True
                    ):
                        success, message = update_user_status(
                            selected_user,
                            False
                        )

                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                else:
                    if st.button(
                        "启用该账号",
                        use_container_width=True
                    ):
                        success, message = update_user_status(
                            selected_user,
                            True
                        )

                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)

                st.divider()
                st.subheader("重置用户密码")

                reset_password = st.text_input(
                    "新密码",
                    type="password",
                    key="reset_password_input"
                )

                if st.button(
                    "确认重置密码",
                    use_container_width=True
                ):
                    success, message = reset_user_password(
                        selected_user,
                        reset_password
                    )

                    if success:
                        st.success(message)
                    else:
                        st.error(message)


def require_login():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    try:
        initialize_database()
    except Exception:
        st.error(
            "登录配置读取失败，请检查 .streamlit/secrets.toml 文件。"
        )
        return False

    if st.session_state["authenticated"]:
        with st.sidebar:
            st.success(
                f'当前账号：{st.session_state["username"]}'
            )

            if st.session_state["role"] == "admin":
                st.caption("管理员权限")

            if st.button("退出登录", use_container_width=True):
                username = st.session_state.get("username", "unknown")
                log_event(username, "退出登录", "用户退出系统")

                st.session_state["authenticated"] = False
                st.session_state.pop("username", None)
                st.session_state.pop("role", None)
                st.rerun()

        render_password_panel()
        render_admin_panel()
        render_audit_panel()

        if st.session_state.get("role") == "admin":
            render_admin_dashboard()

        return True

    st.title("🔐 AI 企业经营分析平台")
    st.subheader("用户登录")

    with st.form("login_form"):
        input_username = st.text_input("账号")
        input_password = st.text_input(
            "密码",
            type="password"
        )

        submitted = st.form_submit_button(
            "登录",
            use_container_width=True
        )

    if submitted:
        if authenticate(input_username.strip(), input_password):
            st.rerun()
        else:
            st.error("账号或密码错误，或该账号已被禁用")

    return False
