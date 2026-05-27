"""User Management - Multi-user authentication and role-based access control."""

import streamlit as st
import pandas as pd
from datetime import datetime
from multi_user_auth import AuthenticationManager, AccessControl, RoleBasedAccessControl, UserRole

st.set_page_config(page_title="User Management", layout="wide")

st.title("🔐 User Management & Authentication")
st.markdown("Manage users, roles, and permissions for the trading platform")

# Initialize session state
if 'auth_manager' not in st.session_state:
    st.session_state.auth_manager = AuthenticationManager("groww_secret_key_production")

if 'current_user' not in st.session_state:
    st.session_state.current_user = None

if 'current_token' not in st.session_state:
    st.session_state.current_token = None

auth_mgr = st.session_state.auth_manager

# Tabs for different operations
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔑 Login",
    "📝 Register",
    "👥 User Management",
    "🔓 Active Sessions",
    "🛡️ Permissions"
])

# ============ LOGIN TAB ============
with tab1:
    st.header("Login to Platform")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        login_username = st.text_input("Username", key="login_user")
        login_password = st.text_input("Password", type="password", key="login_pass")
        
        if st.button("🔐 Login", key="login_btn", use_container_width=True):
            if login_username and login_password:
                success, auth_token, msg = auth_mgr.login(login_username, login_password)
                
                if success:
                    st.session_state.current_user = auth_token
                    st.session_state.current_token = auth_token.token
                    st.success(f"✅ {msg}")
                    st.info(f"Welcome, {auth_token.username}! Role: **{auth_token.role.value.upper()}**")
                else:
                    st.error(f"❌ Login failed: {msg}")
            else:
                st.warning("⚠️ Please enter username and password")
    
    with col2:
        if st.session_state.current_user:
            st.success(f"✅ Logged in as: **{st.session_state.current_user.username}**")
            st.info(f"Role: {st.session_state.current_user.role.value.upper()}")
            st.info(f"Expires at: {st.session_state.current_user.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if st.button("🔓 Logout", use_container_width=True):
                auth_mgr.logout(st.session_state.current_token)
                st.session_state.current_user = None
                st.session_state.current_token = None
                st.success("✅ Logged out successfully")
        else:
            st.warning("❌ Not logged in")
            st.info("Please login first to access the platform")

# ============ REGISTER TAB ============
with tab2:
    st.header("Register New User")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        reg_username = st.text_input("Username", key="reg_user")
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input("Password", type="password", key="reg_pass")
        reg_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")
    
    with col2:
        reg_role = st.selectbox(
            "User Role",
            options=[r.value.upper() for r in UserRole],
            key="reg_role"
        )
        
        # Role descriptions
        role_descriptions = {
            "ADMIN": "Full access to all features and user management",
            "TRADER": "Can execute orders, view positions, manage strategies",
            "ANALYST": "Can view data, create strategies, no order execution",
            "VIEWER": "Read-only access to dashboards and reports"
        }
        
        st.info(role_descriptions.get(reg_role, ""))
    
    if st.button("📝 Register User", use_container_width=True):
        if not all([reg_username, reg_email, reg_password, reg_confirm]):
            st.error("❌ All fields are required")
        elif reg_password != reg_confirm:
            st.error("❌ Passwords don't match")
        elif len(reg_password) < 8:
            st.error("❌ Password must be at least 8 characters")
        else:
            success, user, msg = auth_mgr.register(reg_username, reg_email, reg_password, reg_role.lower())
            
            if success:
                st.success(f"✅ User registered successfully!")
                st.info(f"Username: **{user.username}**")
                st.info(f"Email: **{user.email}**")
                st.info(f"Role: **{user.role.value.upper()}**")
                st.balloons()
            else:
                st.error(f"❌ Registration failed: {msg}")

# ============ USER MANAGEMENT TAB ============
with tab3:
    st.header("User Management")
    
    if st.session_state.current_user and st.session_state.current_user.role == UserRole.ADMIN:
        # List all users
        users_data = []
        for user_id, user in auth_mgr.users.items():
            users_data.append({
                'User ID': user_id[:12] + "...",
                'Username': user.username,
                'Email': user.email,
                'Role': user.role.value.upper(),
                'Active': "✅" if user.is_active else "❌",
                'Created': user.created_at.strftime('%Y-%m-%d %H:%M'),
                'Last Login': user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else "Never"
            })
        
        if users_data:
            df_users = pd.DataFrame(users_data)
            st.dataframe(df_users, use_container_width=True)
        else:
            st.info("ℹ️ No users registered yet")
        
        # User actions
        st.subheader("User Actions")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            select_user = st.selectbox(
                "Select user to manage",
                options=[u.username for u in auth_mgr.users.values()]
            )
            
            if select_user:
                selected_user = next((u for u in auth_mgr.users.values() if u.username == select_user), None)
                
                col_a, col_b = st.columns([1, 1])
                
                with col_a:
                    if selected_user.is_active:
                        if st.button(f"🔒 Disable {select_user}", use_container_width=True):
                            selected_user.is_active = False
                            st.success(f"✅ User {select_user} disabled")
                    else:
                        if st.button(f"🔓 Enable {select_user}", use_container_width=True):
                            selected_user.is_active = True
                            st.success(f"✅ User {select_user} enabled")
                
                with col_b:
                    if st.button(f"🗑️ Delete {select_user}", use_container_width=True):
                        del auth_mgr.users[selected_user.user_id]
                        st.success(f"✅ User {select_user} deleted")
                        st.rerun()
        
        with col2:
            st.info("User Roles:")
            for role in UserRole:
                count = sum(1 for u in auth_mgr.users.values() if u.role == role)
                st.write(f"**{role.value.upper()}**: {count} user(s)")
    
    else:
        st.warning("⚠️ Only ADMIN users can manage other users")
        st.info("Please login as an ADMIN to access this section")

# ============ ACTIVE SESSIONS TAB ============
with tab4:
    st.header("Active Sessions")
    
    if st.session_state.current_user:
        sessions_data = []
        for token, auth_token in auth_mgr.sessions.items():
            is_valid = auth_token.is_valid()
            sessions_data.append({
                'User': auth_token.username,
                'Role': auth_token.role.value.upper(),
                'Status': "✅ Valid" if is_valid else "❌ Expired",
                'Expires At': auth_token.expires_at.strftime('%Y-%m-%d %H:%M:%S'),
                'Token': token[:20] + "..."
            })
        
        if sessions_data:
            df_sessions = pd.DataFrame(sessions_data)
            st.dataframe(df_sessions, use_container_width=True)
            
            st.metric("Active Sessions", len([s for s in sessions_data if "Valid" in s['Status']]))
        else:
            st.info("ℹ️ No active sessions")
    
    else:
        st.warning("⚠️ Please login to view active sessions")

# ============ PERMISSIONS TAB ============
with tab5:
    st.header("Role-Based Permissions")
    
    st.markdown("""
    ### Permission Matrix
    Each role has specific permissions for different resources and actions.
    """)
    
    # Display permission matrix
    rbac = RoleBasedAccessControl()
    
    for role in UserRole:
        with st.expander(f"📋 **{role.value.upper()}** Role Permissions"):
            permissions = rbac.get_role_permissions(role)
            
            if permissions:
                perms_grouped = {}
                for perm in permissions:
                    if perm.resource not in perms_grouped:
                        perms_grouped[perm.resource] = []
                    perms_grouped[perm.resource].append(perm.action)
                
                cols = st.columns(2)
                col_idx = 0
                
                for resource, actions in perms_grouped.items():
                    with cols[col_idx % 2]:
                        st.markdown(f"**{resource.upper()}**")
                        for action in actions:
                            st.write(f"  ✅ {action}")
                    col_idx += 1
            else:
                st.write("No permissions assigned")
    
    # Current user permissions
    if st.session_state.current_user:
        st.divider()
        st.subheader(f"Your Permissions ({st.session_state.current_user.role.value.upper()})")
        
        access_control = AccessControl(auth_mgr)
        permissions = rbac.get_role_permissions(st.session_state.current_user.role)
        
        perm_list = []
        for perm in permissions:
            perm_list.append(f"**{perm.resource}**: {perm.action}")
        
        st.write("\n".join(perm_list))
