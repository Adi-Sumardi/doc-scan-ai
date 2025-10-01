"""
Audit Logging System for Security Events
Tracks authentication attempts, admin actions, and security events
"""
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path
import json

# Create logs directory if not exists
LOGS_DIR = Path(__file__).parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Configure audit logger
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)

# File handler for audit logs
audit_log_file = LOGS_DIR / "audit.log"
file_handler = logging.FileHandler(audit_log_file)
file_handler.setLevel(logging.INFO)

# JSON formatter for structured logs
class JSONFormatter(logging.Formatter):
    """Format logs as JSON for easy parsing"""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "event_type": getattr(record, "event_type", "unknown"),
            "actor": getattr(record, "actor", "system"),
            "action": getattr(record, "action", "unknown"),
            "target": getattr(record, "target", None),
            "ip_address": getattr(record, "ip_address", None),
            "details": getattr(record, "details", {}),
            "status": getattr(record, "status", "unknown"),
            "message": record.getMessage()
        }
        return json.dumps(log_data)

file_handler.setFormatter(JSONFormatter())
audit_logger.addHandler(file_handler)

# Prevent propagation to root logger
audit_logger.propagate = False


class AuditLogger:
    """Centralized audit logging for security events"""
    
    @staticmethod
    def log_event(
        event_type: str,
        action: str,
        actor: str,
        status: str,
        target: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[dict] = None
    ):
        """
        Log a security event
        
        Args:
            event_type: Type of event (auth, admin, security, etc.)
            action: Specific action taken
            actor: User or system performing action
            status: Result status (success, failure, blocked, etc.)
            target: Target of the action (user_id, resource, etc.)
            ip_address: IP address of the actor
            details: Additional context
        """
        extra = {
            "event_type": event_type,
            "action": action,
            "actor": actor,
            "status": status,
            "target": target,
            "ip_address": ip_address,
            "details": details or {}
        }
        
        message = f"{event_type.upper()}: {action} by {actor} - {status}"
        if target:
            message += f" (target: {target})"
        
        audit_logger.info(message, extra=extra)
    
    @staticmethod
    def log_authentication(
        username: str,
        action: str,
        status: str,
        ip_address: Optional[str] = None,
        details: Optional[dict] = None
    ):
        """Log authentication events"""
        AuditLogger.log_event(
            event_type="authentication",
            action=action,
            actor=username,
            status=status,
            ip_address=ip_address,
            details=details
        )
    
    @staticmethod
    def log_admin_action(
        admin_username: str,
        action: str,
        target_user: str,
        status: str,
        ip_address: Optional[str] = None,
        details: Optional[dict] = None
    ):
        """Log admin actions"""
        AuditLogger.log_event(
            event_type="admin_action",
            action=action,
            actor=admin_username,
            target=target_user,
            status=status,
            ip_address=ip_address,
            details=details
        )
    
    @staticmethod
    def log_security_event(
        event: str,
        actor: str,
        status: str,
        ip_address: Optional[str] = None,
        details: Optional[dict] = None
    ):
        """Log security events (rate limit, injection attempts, etc.)"""
        AuditLogger.log_event(
            event_type="security",
            action=event,
            actor=actor,
            status=status,
            ip_address=ip_address,
            details=details
        )
    
    @staticmethod
    def log_data_access(
        username: str,
        resource: str,
        action: str,
        status: str,
        ip_address: Optional[str] = None,
        details: Optional[dict] = None
    ):
        """Log data access events"""
        AuditLogger.log_event(
            event_type="data_access",
            action=action,
            actor=username,
            target=resource,
            status=status,
            ip_address=ip_address,
            details=details
        )


# Convenience functions
def log_login_success(username: str, ip_address: str):
    """Log successful login"""
    AuditLogger.log_authentication(
        username=username,
        action="login",
        status="success",
        ip_address=ip_address
    )


def log_login_failure(username: str, ip_address: str, reason: str = "invalid_credentials"):
    """Log failed login attempt"""
    AuditLogger.log_authentication(
        username=username,
        action="login",
        status="failure",
        ip_address=ip_address,
        details={"reason": reason}
    )


def log_registration(username: str, ip_address: str, status: str = "success"):
    """Log user registration"""
    AuditLogger.log_authentication(
        username=username,
        action="register",
        status=status,
        ip_address=ip_address
    )


def log_password_reset(admin_username: str, target_username: str, ip_address: str):
    """Log password reset by admin"""
    AuditLogger.log_admin_action(
        admin_username=admin_username,
        action="password_reset",
        target_user=target_username,
        status="success",
        ip_address=ip_address
    )


def log_user_status_change(admin_username: str, target_username: str, new_status: bool, ip_address: str):
    """Log user activation/deactivation"""
    action = "user_activated" if new_status else "user_deactivated"
    AuditLogger.log_admin_action(
        admin_username=admin_username,
        action=action,
        target_user=target_username,
        status="success",
        ip_address=ip_address,
        details={"new_status": new_status}
    )


def log_rate_limit_exceeded(username: str, endpoint: str, ip_address: str):
    """Log rate limit exceeded"""
    AuditLogger.log_security_event(
        event="rate_limit_exceeded",
        actor=username or "anonymous",
        status="blocked",
        ip_address=ip_address,
        details={"endpoint": endpoint}
    )


def log_injection_attempt(username: str, attack_type: str, ip_address: str, payload: str):
    """Log injection attack attempt"""
    AuditLogger.log_security_event(
        event=f"{attack_type}_injection_attempt",
        actor=username or "anonymous",
        status="blocked",
        ip_address=ip_address,
        details={"payload": payload[:100]}  # Limit payload length
    )
