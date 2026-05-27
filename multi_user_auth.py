"""Multi-User Authentication & RBAC - Role-based access control."""

import jwt
import hashlib
import secrets
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class UserRole(Enum):
    """User roles in the trading system."""
    ADMIN = "admin"
    TRADER = "trader"
    ANALYST = "analyst"
    VIEWER = "viewer"

@dataclass
class Permission:
    """Permission definition."""
    resource: str  # e.g., 'orders', 'positions', 'settings'
    action: str    # e.g., 'create', 'read', 'update', 'delete'
    
    def __str__(self):
        return f"{self.resource}:{self.action}"

class RoleBasedAccessControl:
    """RBAC configuration for trading system."""
    
    # Define permissions for each role
    ROLE_PERMISSIONS = {
        UserRole.ADMIN: [
            Permission("orders", "create"),
            Permission("orders", "read"),
            Permission("orders", "update"),
            Permission("orders", "delete"),
            Permission("positions", "create"),
            Permission("positions", "read"),
            Permission("positions", "update"),
            Permission("positions", "delete"),
            Permission("settings", "read"),
            Permission("settings", "update"),
            Permission("users", "create"),
            Permission("users", "read"),
            Permission("users", "update"),
            Permission("users", "delete"),
            Permission("audit_log", "read"),
            Permission("reports", "read"),
            Permission("strategies", "create"),
            Permission("strategies", "read"),
            Permission("strategies", "update"),
            Permission("strategies", "delete")
        ],
        UserRole.TRADER: [
            Permission("orders", "create"),
            Permission("orders", "read"),
            Permission("orders", "update"),
            Permission("positions", "read"),
            Permission("settings", "read"),
            Permission("positions", "update"),  # Can update SL/target
            Permission("strategies", "read"),
            Permission("audit_log", "read"),
            Permission("reports", "read")
        ],
        UserRole.ANALYST: [
            Permission("positions", "read"),
            Permission("orders", "read"),
            Permission("strategies", "read"),
            Permission("reports", "read"),
            Permission("audit_log", "read"),
            Permission("settings", "read")  # Read-only settings
        ],
        UserRole.VIEWER: [
            Permission("positions", "read"),
            Permission("orders", "read"),
            Permission("reports", "read"),
            Permission("strategies", "read")
        ]
    }
    
    @classmethod
    def has_permission(cls, role: UserRole, permission: Permission) -> bool:
        """Check if role has specific permission."""
        
        role_perms = cls.ROLE_PERMISSIONS.get(role, [])
        return permission in role_perms
    
    @classmethod
    def get_role_permissions(cls, role: UserRole) -> List[Permission]:
        """Get all permissions for a role."""
        
        return cls.ROLE_PERMISSIONS.get(role, [])

@dataclass
class User:
    """User account."""
    user_id: str
    username: str
    email: str
    role: UserRole
    password_hash: str
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    mfa_enabled: bool = False
    
    def verify_password(self, password: str) -> bool:
        """Verify password against hash."""
        return self._hash_password(password) == self.password_hash
    
    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash password using SHA-256."""
        salt = "groww_trading_salt"  # In production, use per-user salt
        return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    
    @classmethod
    def create(cls, username: str, email: str, password: str, role: UserRole) -> 'User':
        """Create new user."""
        
        user = cls(
            user_id=secrets.token_urlsafe(12),
            username=username,
            email=email,
            role=role,
            password_hash=cls._hash_password(password),
            created_at=datetime.now()
        )
        
        logger.info(f"✅ User created: {username} ({role.value})")
        return user

@dataclass
class AuthToken:
    """JWT authentication token."""
    token: str
    user_id: str
    username: str
    role: UserRole
    expires_at: datetime
    
    def is_valid(self) -> bool:
        """Check if token is still valid."""
        return datetime.now() < self.expires_at
    
    def is_expired(self) -> bool:
        """Check if token has expired."""
        return datetime.now() >= self.expires_at

class AuthenticationManager:
    """Handle user authentication and token generation."""
    
    def __init__(self, secret_key: str = "groww_secret_key"):
        self.secret_key = secret_key
        self.token_expiry_hours = 24
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, AuthToken] = {}
    
    def register(self, username: str, email: str, password: str, role: UserRole) -> Tuple[bool, str]:
        """Register new user."""
        
        # Check if username exists
        if any(u.username == username for u in self.users.values()):
            return False, "Username already exists"
        
        # Check email
        if any(u.email == email for u in self.users.values()):
            return False, "Email already exists"
        
        # Create user
        user = User.create(username, email, password, role)
        self.users[user.user_id] = user
        
        logger.info(f"✅ User registered: {username}")
        return True, "User registered successfully"
    
    def login(self, username: str, password: str) -> Tuple[bool, Optional[AuthToken], str]:
        """Authenticate user and generate token."""
        
        # Find user
        user = next((u for u in self.users.values() if u.username == username), None)
        
        if not user:
            return False, None, "User not found"
        
        if not user.is_active:
            return False, None, "User account is inactive"
        
        if not user.verify_password(password):
            return False, None, "Invalid password"
        
        # Generate JWT token
        expires_at = datetime.now() + timedelta(hours=self.token_expiry_hours)
        
        token_data = {
            'user_id': user.user_id,
            'username': user.username,
            'role': user.role.value,
            'exp': int(expires_at.timestamp())
        }
        
        token = jwt.encode(token_data, self.secret_key, algorithm="HS256")
        
        auth_token = AuthToken(
            token=token,
            user_id=user.user_id,
            username=user.username,
            role=user.role,
            expires_at=expires_at
        )
        
        self.sessions[token] = auth_token
        user.last_login = datetime.now()
        
        logger.info(f"✅ User logged in: {username}")
        return True, auth_token, "Login successful"
    
    def verify_token(self, token: str) -> Tuple[bool, Optional[User], str]:
        """Verify JWT token and return user."""
        
        try:
            # Check if token is in cache
            if token in self.sessions:
                auth_token = self.sessions[token]
                if auth_token.is_valid():
                    user = self.users.get(auth_token.user_id)
                    if user:
                        return True, user, "Token valid"
                else:
                    del self.sessions[token]
                    return False, None, "Token expired"
            
            # Decode JWT
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            
            user_id = payload.get('user_id')
            user = self.users.get(user_id)
            
            if user:
                return True, user, "Token verified"
            else:
                return False, None, "User not found"
        
        except jwt.ExpiredSignatureError:
            return False, None, "Token expired"
        except jwt.InvalidTokenError:
            return False, None, "Invalid token"
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return False, None, str(e)
    
    def logout(self, token: str) -> bool:
        """Logout user and invalidate token."""
        
        if token in self.sessions:
            del self.sessions[token]
            logger.info("✅ User logged out")
            return True
        return False

class AccessControl:
    """Check if user has access to resource/action."""
    
    def __init__(self, auth_manager: AuthenticationManager):
        self.auth = auth_manager
        self.rbac = RoleBasedAccessControl()
    
    def can_access(self, token: str, resource: str, action: str) -> Tuple[bool, str]:
        """Check if user can access resource with action."""
        
        valid, user, msg = self.auth.verify_token(token)
        
        if not valid:
            return False, f"Authentication failed: {msg}"
        
        permission = Permission(resource, action)
        
        if self.rbac.has_permission(user.role, permission):
            logger.info(f"✅ Access granted: {user.username} -> {permission}")
            return True, "Access granted"
        else:
            logger.warning(f"❌ Access denied: {user.username} -> {permission}")
            return False, f"Access denied: {permission}"
    
    def require_role(self, token: str, required_roles: List[UserRole]) -> Tuple[bool, str]:
        """Check if user has required role."""
        
        valid, user, msg = self.auth.verify_token(token)
        
        if not valid:
            return False, f"Authentication failed: {msg}"
        
        if user.role in required_roles:
            return True, f"Role requirement met: {user.role.value}"
        else:
            return False, f"Insufficient permissions: requires one of {[r.value for r in required_roles]}"

class AuditLog:
    """Audit trail for security events."""
    
    def __init__(self):
        self.logs: List[Dict[str, Any]] = []
    
    def log_login(self, username: str, success: bool) -> None:
        """Log login attempt."""
        
        self.logs.append({
            'timestamp': datetime.now(),
            'event_type': 'LOGIN',
            'username': username,
            'status': 'SUCCESS' if success else 'FAILED'
        })
    
    def log_access(self, username: str, resource: str, action: str, granted: bool) -> None:
        """Log resource access attempt."""
        
        self.logs.append({
            'timestamp': datetime.now(),
            'event_type': 'ACCESS',
            'username': username,
            'resource': resource,
            'action': action,
            'status': 'GRANTED' if granted else 'DENIED'
        })
    
    def log_order(self, username: str, symbol: str, side: str, qty: int, price: float) -> None:
        """Log order execution."""
        
        self.logs.append({
            'timestamp': datetime.now(),
            'event_type': 'ORDER',
            'username': username,
            'symbol': symbol,
            'side': side,
            'quantity': qty,
            'price': price
        })
    
    def get_logs(self, username: str = None, event_type: str = None, 
                 hours: int = 24) -> List[Dict[str, Any]]:
        """Query audit logs."""
        
        cutoff = datetime.now() - timedelta(hours=hours)
        
        results = [log for log in self.logs if log['timestamp'] >= cutoff]
        
        if username:
            results = [log for log in results if log.get('username') == username]
        
        if event_type:
            results = [log for log in results if log.get('event_type') == event_type]
        
        return results

# Example usage
def example_auth_system():
    """Example multi-user auth system."""
    
    # Initialize
    auth = AuthenticationManager()
    access = AccessControl(auth)
    audit = AuditLog()
    
    # Register users
    print("Registering users...")
    auth.register("admin", "admin@groww.com", "admin123", UserRole.ADMIN)
    auth.register("trader1", "trader@groww.com", "trader123", UserRole.TRADER)
    auth.register("analyst", "analyst@groww.com", "analyst123", UserRole.ANALYST)
    
    # Login
    print("\nLogging in...")
    success, token, msg = auth.login("trader1", "trader123")
    print(f"Login: {msg}")
    
    # Check access
    print("\nChecking access...")
    can_trade, msg = access.can_access(token.token, "orders", "create")
    print(f"Can create order: {can_trade} - {msg}")
    
    can_admin, msg = access.can_access(token.token, "users", "delete")
    print(f"Can delete users: {can_admin} - {msg}")
    
    # Verify token
    print("\nVerifying token...")
    valid, user, msg = auth.verify_token(token.token)
    print(f"Token valid: {valid} - User: {user.username if valid else 'N/A'}")
    
    print("\n✅ Multi-user auth system complete!")

if __name__ == "__main__":
    example_auth_system()
