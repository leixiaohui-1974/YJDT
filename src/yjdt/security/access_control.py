# -*- coding: utf-8 -*-
"""
访问控制系统 - 基于角色的权限管理
Access Control System - Role-Based Access Control (RBAC)

功能：
- 用户身份认证
- 角色权限管理
- 操作审计
- 多因素认证支持
"""

import hashlib
import secrets
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
from enum import Enum


class AuthResult(Enum):
    """认证结果"""
    SUCCESS = "success"
    FAILED = "failed"
    LOCKED = "locked"
    EXPIRED = "expired"
    MFA_REQUIRED = "mfa_required"


@dataclass
class Permission:
    """权限定义"""
    permission_id: str
    name: str
    description: str
    resource: str                           # 资源类型
    actions: Set[str] = field(default_factory=set)  # 允许的操作


@dataclass
class Role:
    """角色定义"""
    role_id: str
    name: str
    description: str
    permissions: Set[str] = field(default_factory=set)  # 权限ID集合
    level: int = 0                          # 权限级别


@dataclass
class User:
    """用户"""
    user_id: str
    username: str
    password_hash: str
    roles: Set[str] = field(default_factory=set)
    enabled: bool = True
    locked: bool = False
    failed_attempts: int = 0
    last_login: Optional[datetime] = None
    password_expires: Optional[datetime] = None
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None


@dataclass
class AuditLog:
    """审计日志"""
    log_id: str
    user_id: str
    action: str
    resource: str
    result: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source_ip: Optional[str] = None


class AccessController:
    """
    访问控制器

    功能：
    - 用户认证与授权
    - 角色权限管理
    - 操作审计
    - 安全策略执行
    """

    def __init__(self):
        self.users: Dict[str, User] = {}
        self.roles: Dict[str, Role] = {}
        self.permissions: Dict[str, Permission] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.audit_logs: List[AuditLog] = []

        # 安全策略
        self.policy = {
            "max_failed_attempts": 5,
            "lockout_duration": 300,        # 秒
            "session_timeout": 3600,        # 秒
            "password_min_length": 8,
            "password_expires_days": 90,
            "require_mfa": False,
        }

        self._log_counter = 0

        # 初始化默认角色和权限
        self._initialize_defaults()

    def _initialize_defaults(self):
        """初始化默认角色和权限"""
        # 定义权限
        default_permissions = [
            Permission("PERM_VIEW_STATUS", "查看状态", "查看系统运行状态", "status", {"read"}),
            Permission("PERM_VIEW_ALARM", "查看报警", "查看报警信息", "alarm", {"read"}),
            Permission("PERM_ACK_ALARM", "确认报警", "确认报警信息", "alarm", {"read", "acknowledge"}),
            Permission("PERM_CONTROL", "控制操作", "执行控制操作", "control", {"read", "write"}),
            Permission("PERM_SETPOINT", "设定修改", "修改设定值", "setpoint", {"read", "write"}),
            Permission("PERM_CONFIG", "配置管理", "系统配置管理", "config", {"read", "write"}),
            Permission("PERM_USER_MGMT", "用户管理", "用户账户管理", "user", {"read", "write", "delete"}),
            Permission("PERM_OVERRIDE", "强制操作", "强制越权操作", "override", {"execute"}),
            Permission("PERM_EMERGENCY", "应急操作", "应急响应操作", "emergency", {"execute"}),
        ]

        for perm in default_permissions:
            self.permissions[perm.permission_id] = perm

        # 定义角色
        default_roles = [
            Role(
                role_id="ROLE_VIEWER",
                name="观察员",
                description="只读访问权限",
                permissions={"PERM_VIEW_STATUS", "PERM_VIEW_ALARM"},
                level=1
            ),
            Role(
                role_id="ROLE_OPERATOR",
                name="操作员",
                description="日常操作权限",
                permissions={"PERM_VIEW_STATUS", "PERM_VIEW_ALARM", "PERM_ACK_ALARM",
                            "PERM_CONTROL", "PERM_SETPOINT"},
                level=2
            ),
            Role(
                role_id="ROLE_ENGINEER",
                name="工程师",
                description="配置和维护权限",
                permissions={"PERM_VIEW_STATUS", "PERM_VIEW_ALARM", "PERM_ACK_ALARM",
                            "PERM_CONTROL", "PERM_SETPOINT", "PERM_CONFIG"},
                level=3
            ),
            Role(
                role_id="ROLE_SUPERVISOR",
                name="值长",
                description="监督和应急权限",
                permissions={"PERM_VIEW_STATUS", "PERM_VIEW_ALARM", "PERM_ACK_ALARM",
                            "PERM_CONTROL", "PERM_SETPOINT", "PERM_OVERRIDE", "PERM_EMERGENCY"},
                level=4
            ),
            Role(
                role_id="ROLE_ADMIN",
                name="管理员",
                description="完全管理权限",
                permissions=set(self.permissions.keys()),
                level=5
            ),
        ]

        for role in default_roles:
            self.roles[role.role_id] = role

        # 创建默认管理员
        self.create_user("admin", "admin123", {"ROLE_ADMIN"})
        self.create_user("operator1", "oper123", {"ROLE_OPERATOR"})
        self.create_user("engineer1", "eng123", {"ROLE_ENGINEER"})

    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        salt = "yjdt_salt_2024"  # 实际应用中应使用随机盐
        return hashlib.sha256((password + salt).encode()).hexdigest()

    def create_user(self, username: str, password: str,
                    roles: Set[str], mfa_enabled: bool = False) -> Optional[User]:
        """创建用户"""
        if username in [u.username for u in self.users.values()]:
            return None

        user_id = f"USER_{len(self.users):04d}"
        password_hash = self._hash_password(password)

        user = User(
            user_id=user_id,
            username=username,
            password_hash=password_hash,
            roles=roles,
            mfa_enabled=mfa_enabled,
            password_expires=datetime.now() + timedelta(days=self.policy["password_expires_days"]),
        )

        self.users[user_id] = user
        self._audit("create_user", user_id, "user", "success", {"username": username})

        return user

    def authenticate(self, username: str, password: str,
                     source_ip: Optional[str] = None) -> tuple:
        """
        用户认证

        Returns:
            (AuthResult, session_token或None, User或None)
        """
        # 查找用户
        user = None
        for u in self.users.values():
            if u.username == username:
                user = u
                break

        if not user:
            self._audit("login_failed", "unknown", "auth", "failed",
                       {"username": username, "reason": "user_not_found"}, source_ip)
            return (AuthResult.FAILED, None, None)

        # 检查锁定
        if user.locked:
            self._audit("login_failed", user.user_id, "auth", "locked",
                       {"reason": "account_locked"}, source_ip)
            return (AuthResult.LOCKED, None, None)

        # 检查启用状态
        if not user.enabled:
            return (AuthResult.FAILED, None, None)

        # 验证密码
        if self._hash_password(password) != user.password_hash:
            user.failed_attempts += 1

            # 检查是否需要锁定
            if user.failed_attempts >= self.policy["max_failed_attempts"]:
                user.locked = True
                self._audit("account_locked", user.user_id, "auth", "locked",
                           {"failed_attempts": user.failed_attempts}, source_ip)

            self._audit("login_failed", user.user_id, "auth", "failed",
                       {"reason": "wrong_password"}, source_ip)
            return (AuthResult.FAILED, None, None)

        # 检查密码过期
        if user.password_expires and datetime.now() > user.password_expires:
            self._audit("login_failed", user.user_id, "auth", "expired",
                       {"reason": "password_expired"}, source_ip)
            return (AuthResult.EXPIRED, None, None)

        # 检查MFA
        if user.mfa_enabled or self.policy["require_mfa"]:
            # 实际应用中这里应该验证MFA令牌
            pass

        # 认证成功
        user.failed_attempts = 0
        user.last_login = datetime.now()

        # 创建会话
        session_token = secrets.token_hex(32)
        self.sessions[session_token] = {
            "user_id": user.user_id,
            "created": datetime.now(),
            "expires": datetime.now() + timedelta(seconds=self.policy["session_timeout"]),
            "source_ip": source_ip,
        }

        self._audit("login_success", user.user_id, "auth", "success",
                   {"source_ip": source_ip}, source_ip)

        return (AuthResult.SUCCESS, session_token, user)

    def validate_session(self, session_token: str) -> Optional[User]:
        """验证会话"""
        if session_token not in self.sessions:
            return None

        session = self.sessions[session_token]

        # 检查过期
        if datetime.now() > session["expires"]:
            del self.sessions[session_token]
            return None

        user_id = session["user_id"]
        return self.users.get(user_id)

    def logout(self, session_token: str):
        """登出"""
        if session_token in self.sessions:
            user_id = self.sessions[session_token]["user_id"]
            del self.sessions[session_token]
            self._audit("logout", user_id, "auth", "success")

    def check_permission(self, user: User, resource: str, action: str) -> bool:
        """检查权限"""
        if not user or not user.enabled or user.locked:
            return False

        # 收集用户所有权限
        user_permissions = set()
        for role_id in user.roles:
            if role_id in self.roles:
                user_permissions.update(self.roles[role_id].permissions)

        # 检查权限
        for perm_id in user_permissions:
            if perm_id in self.permissions:
                perm = self.permissions[perm_id]
                if perm.resource == resource and action in perm.actions:
                    return True

        return False

    def authorize(self, session_token: str, resource: str, action: str) -> bool:
        """授权检查"""
        user = self.validate_session(session_token)
        if not user:
            return False

        allowed = self.check_permission(user, resource, action)

        self._audit(
            f"authorize_{action}",
            user.user_id,
            resource,
            "success" if allowed else "denied"
        )

        return allowed

    def _audit(self, action: str, user_id: str, resource: str,
               result: str, details: Dict[str, Any] = None,
               source_ip: Optional[str] = None):
        """记录审计日志"""
        self._log_counter += 1
        log_id = f"LOG_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self._log_counter:06d}"

        log = AuditLog(
            log_id=log_id,
            user_id=user_id,
            action=action,
            resource=resource,
            result=result,
            details=details or {},
            source_ip=source_ip,
        )

        self.audit_logs.append(log)

        # 限制日志数量
        if len(self.audit_logs) > 100000:
            self.audit_logs = self.audit_logs[-100000:]

    def get_audit_logs(self, user_id: Optional[str] = None,
                       action: Optional[str] = None,
                       time_range: Optional[timedelta] = None,
                       limit: int = 100) -> List[Dict[str, Any]]:
        """获取审计日志"""
        logs = self.audit_logs

        if user_id:
            logs = [l for l in logs if l.user_id == user_id]

        if action:
            logs = [l for l in logs if action in l.action]

        if time_range:
            cutoff = datetime.now() - time_range
            logs = [l for l in logs if l.timestamp >= cutoff]

        # 按时间倒序
        logs = sorted(logs, key=lambda l: l.timestamp, reverse=True)

        return [
            {
                "log_id": l.log_id,
                "user_id": l.user_id,
                "action": l.action,
                "resource": l.resource,
                "result": l.result,
                "timestamp": l.timestamp.isoformat(),
                "source_ip": l.source_ip,
                "details": l.details,
            }
            for l in logs[:limit]
        ]

    def change_password(self, user_id: str, old_password: str,
                        new_password: str) -> bool:
        """修改密码"""
        if user_id not in self.users:
            return False

        user = self.users[user_id]

        # 验证旧密码
        if self._hash_password(old_password) != user.password_hash:
            self._audit("password_change", user_id, "user", "failed",
                       {"reason": "wrong_old_password"})
            return False

        # 检查密码强度
        if len(new_password) < self.policy["password_min_length"]:
            return False

        user.password_hash = self._hash_password(new_password)
        user.password_expires = datetime.now() + timedelta(days=self.policy["password_expires_days"])

        self._audit("password_change", user_id, "user", "success")
        return True

    def unlock_user(self, admin_user: User, target_user_id: str) -> bool:
        """解锁用户账户"""
        if not self.check_permission(admin_user, "user", "write"):
            return False

        if target_user_id not in self.users:
            return False

        user = self.users[target_user_id]
        user.locked = False
        user.failed_attempts = 0

        self._audit("unlock_user", admin_user.user_id, "user", "success",
                   {"target_user": target_user_id})
        return True

    def get_user_summary(self) -> Dict[str, Any]:
        """获取用户摘要"""
        return {
            "total_users": len(self.users),
            "active_users": sum(1 for u in self.users.values() if u.enabled),
            "locked_users": sum(1 for u in self.users.values() if u.locked),
            "active_sessions": len(self.sessions),
            "roles": list(self.roles.keys()),
            "permissions": list(self.permissions.keys()),
        }
