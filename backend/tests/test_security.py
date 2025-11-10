"""Tests for security features: Rate Limiting, JWT Refresh Tokens, and RBAC."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.models import RefreshToken, User, UserRole
from app.services.auth_service import auth_service


# ============================================
# RATE LIMITING TESTS
# ============================================

class TestRateLimiting:
    """Test rate limiting on authentication endpoints."""

    def test_login_rate_limit_exceeded(self, client):
        """Test that login endpoint enforces rate limit (5 per minute)."""
        from app.core.database import SessionLocal

        session = SessionLocal()
        try:
            # Create test user
            password = "test-password"
            user = User(
                username="ratelimit_user",
                email="ratelimit@example.com",
                password_hash=auth_service.get_password_hash(password),
                full_name="Rate Limit Test",
                role=UserRole.EMPLOYEE,
                is_active=True,
            )
            session.add(user)
            session.commit()

            # Attempt login 6 times (rate limit is 5/minute)
            # First 5 should succeed or return 401
            # 6th should return 429 (Too Many Requests)
            responses = []
            for i in range(6):
                response = client.post(
                    "/api/auth/login",
                    data={"username": "ratelimit_user", "password": password},
                )
                responses.append(response)
                time.sleep(0.1)  # Small delay between requests

            # Check that we got rate limited
            status_codes = [r.status_code for r in responses]

            # First 5 should be 200 (successful login)
            assert status_codes[:5] == [200] * 5, f"Expected first 5 to be 200, got {status_codes[:5]}"

            # 6th should be 429 (rate limited)
            assert status_codes[5] == 429, f"Expected 429 for 6th request, got {status_codes[5]}"

        finally:
            session.close()

    def test_register_rate_limit(self, client):
        """Test that register endpoint enforces rate limit (3 per hour)."""
        # Attempt to register 4 users within a short time
        # First 3 should succeed, 4th should be rate limited
        responses = []
        for i in range(4):
            response = client.post(
                "/api/auth/register",
                json={
                    "username": f"newuser_{i}_{int(time.time())}",
                    "email": f"newuser{i}_{int(time.time())}@example.com",
                    "password": "securepassword123",
                    "full_name": f"New User {i}",
                    "role": "EMPLOYEE"
                }
            )
            responses.append(response)
            time.sleep(0.1)

        status_codes = [r.status_code for r in responses]

        # First 3 should succeed (201 Created)
        assert status_codes[:3] == [201] * 3, f"Expected first 3 to be 201, got {status_codes[:3]}"

        # 4th should be rate limited (429)
        assert status_codes[3] == 429, f"Expected 429 for 4th request, got {status_codes[3]}"


# ============================================
# JWT REFRESH TOKEN TESTS
# ============================================

class TestJWTRefreshTokens:
    """Test JWT refresh token functionality."""

    def test_refresh_token_creation(self, client):
        """Test that login creates both access and refresh tokens."""
        from app.core.database import SessionLocal

        session = SessionLocal()
        try:
            # Create test user
            password = "test-password"
            user = User(
                username="refresh_test_user",
                email="refresh@example.com",
                password_hash=auth_service.get_password_hash(password),
                full_name="Refresh Test",
                role=UserRole.EMPLOYEE,
                is_active=True,
            )
            session.add(user)
            session.commit()

            # Login
            response = client.post(
                "/api/auth/login",
                data={"username": "refresh_test_user", "password": password},
            )

            assert response.status_code == 200
            data = response.json()

            # Should have both tokens
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"

            # Verify refresh token was saved to database
            refresh_token = session.query(RefreshToken).filter(
                RefreshToken.token == data["refresh_token"]
            ).first()

            assert refresh_token is not None
            assert refresh_token.user_id == user.id
            assert refresh_token.revoked == False

        finally:
            session.close()

    def test_refresh_token_rotation(self, client):
        """Test that refresh endpoint rotates tokens (revokes old, creates new)."""
        from app.core.database import SessionLocal

        session = SessionLocal()
        try:
            # Create test user
            password = "test-password"
            user = User(
                username="rotation_test_user",
                email="rotation@example.com",
                password_hash=auth_service.get_password_hash(password),
                full_name="Rotation Test",
                role=UserRole.EMPLOYEE,
                is_active=True,
            )
            session.add(user)
            session.commit()

            # Login to get initial tokens
            login_response = client.post(
                "/api/auth/login",
                data={"username": "rotation_test_user", "password": password},
            )
            old_refresh_token = login_response.json()["refresh_token"]

            time.sleep(1)  # Wait a bit before refreshing

            # Use refresh token to get new tokens
            refresh_response = client.post(
                "/api/auth/refresh",
                json={"refresh_token": old_refresh_token}
            )

            assert refresh_response.status_code == 200
            new_data = refresh_response.json()

            assert "access_token" in new_data
            assert "refresh_token" in new_data
            assert new_data["refresh_token"] != old_refresh_token  # Token should be different

            # Verify old token was revoked
            old_token_record = session.query(RefreshToken).filter(
                RefreshToken.token == old_refresh_token
            ).first()

            assert old_token_record is not None
            assert old_token_record.revoked == True
            assert old_token_record.revoked_at is not None

            # Verify new token exists and is not revoked
            new_token_record = session.query(RefreshToken).filter(
                RefreshToken.token == new_data["refresh_token"]
            ).first()

            assert new_token_record is not None
            assert new_token_record.revoked == False

        finally:
            session.close()

    def test_refresh_token_reuse_denied(self, client):
        """Test that using a revoked refresh token fails."""
        from app.core.database import SessionLocal

        session = SessionLocal()
        try:
            # Create test user
            password = "test-password"
            user = User(
                username="reuse_test_user",
                email="reuse@example.com",
                password_hash=auth_service.get_password_hash(password),
                full_name="Reuse Test",
                role=UserRole.EMPLOYEE,
                is_active=True,
            )
            session.add(user)
            session.commit()

            # Login to get tokens
            login_response = client.post(
                "/api/auth/login",
                data={"username": "reuse_test_user", "password": password},
            )
            old_refresh_token = login_response.json()["refresh_token"]

            # Use refresh token once (this revokes it)
            first_refresh = client.post(
                "/api/auth/refresh",
                json={"refresh_token": old_refresh_token}
            )
            assert first_refresh.status_code == 200

            # Try to use the SAME token again (should fail)
            second_refresh = client.post(
                "/api/auth/refresh",
                json={"refresh_token": old_refresh_token}
            )

            assert second_refresh.status_code == 401
            assert "revoked" in second_refresh.json()["detail"].lower()

        finally:
            session.close()

    def test_logout_all_devices(self, client):
        """Test that logout can revoke all refresh tokens for a user."""
        from app.core.database import SessionLocal

        session = SessionLocal()
        try:
            # Create test user
            password = "test-password"
            user = User(
                username="logout_all_user",
                email="logoutall@example.com",
                password_hash=auth_service.get_password_hash(password),
                full_name="Logout All Test",
                role=UserRole.EMPLOYEE,
                is_active=True,
            )
            session.add(user)
            session.commit()

            # Login twice (simulate 2 devices)
            login1 = client.post(
                "/api/auth/login",
                data={"username": "logout_all_user", "password": password},
            )
            token1 = login1.json()["access_token"]
            refresh1 = login1.json()["refresh_token"]

            login2 = client.post(
                "/api/auth/login",
                data={"username": "logout_all_user", "password": password},
            )
            refresh2 = login2.json()["refresh_token"]

            # Logout from all devices
            logout_response = client.post(
                "/api/auth/logout",
                json={
                    "refresh_token": refresh1,
                    "logout_all_devices": True
                },
                headers={"Authorization": f"Bearer {token1}"}
            )

            assert logout_response.status_code == 200
            assert "all devices" in logout_response.json()["message"].lower()

            # Verify both tokens are revoked
            session.expire_all()  # Refresh from DB

            token_record1 = session.query(RefreshToken).filter(
                RefreshToken.token == refresh1
            ).first()
            assert token_record1.revoked == True

            token_record2 = session.query(RefreshToken).filter(
                RefreshToken.token == refresh2
            ).first()
            assert token_record2.revoked == True

        finally:
            session.close()


# ============================================
# RBAC (Role-Based Access Control) TESTS
# ============================================

class TestRBAC:
    """Test Role-Based Access Control with require_role()."""

    @pytest.fixture
    def users_with_roles(self) -> dict[str, tuple[User, str]]:
        """Create test users with different roles."""
        session = SessionLocal()
        try:
            users = {}
            password = "test-password"

            roles = [
                ("super_admin_user", "SUPER_ADMIN"),
                ("admin_user", "ADMIN"),
                ("coordinator_user", "COORDINATOR"),
                ("kanrininsha_user", "KANRININSHA"),
                ("employee_user", "EMPLOYEE"),
                ("contract_worker_user", "CONTRACT_WORKER"),
            ]

            for username, role in roles:
                user = User(
                    username=username,
                    email=f"{username}@example.com",
                    password_hash=auth_service.get_password_hash(password),
                    full_name=f"{role} User",
                    role=UserRole[role],
                    is_active=True,
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                users[role] = (user, password)

            return users
        finally:
            session.close()

    def test_super_admin_only_access(self, client, users_with_roles):
        """Test that only SUPER_ADMIN can access super_admin-protected endpoints."""
        # Login as SUPER_ADMIN
        super_admin_login = client.post(
            "/api/auth/login",
            data={"username": "super_admin_user", "password": "test-password"},
        )
        super_admin_token = super_admin_login.json()["access_token"]

        # Login as ADMIN (should be denied)
        admin_login = client.post(
            "/api/auth/login",
            data={"username": "admin_user", "password": "test-password"},
        )
        admin_token = admin_login.json()["access_token"]

        # Test endpoint that requires super_admin role
        # (using factories endpoint which requires super_admin for DELETE)

        # SUPER_ADMIN should succeed (or get 404 if factory doesn't exist)
        super_response = client.delete(
            "/api/factories/999",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        # Should be 404 (not found) NOT 403 (forbidden)
        assert super_response.status_code in [404, 200, 204]

        # ADMIN should be forbidden (403)
        admin_response = client.delete(
            "/api/factories/999",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_response.status_code == 403
        assert "permissions" in admin_response.json()["detail"].lower()

    def test_admin_access_hierarchy(self, client, users_with_roles):
        """Test that ADMIN can access admin-protected endpoints but EMPLOYEE cannot."""
        # Login as ADMIN
        admin_login = client.post(
            "/api/auth/login",
            data={"username": "admin_user", "password": "test-password"},
        )
        admin_token = admin_login.json()["access_token"]

        # Login as EMPLOYEE
        employee_login = client.post(
            "/api/auth/login",
            data={"username": "employee_user", "password": "test-password"},
        )
        employee_token = employee_login.json()["access_token"]

        # Test endpoint that requires admin role
        # (using timer_cards endpoint which requires admin)

        # ADMIN should have access (might get 404 if no data)
        admin_response = client.delete(
            "/api/timer-cards/999",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Should NOT be 403 (forbidden)
        assert admin_response.status_code != 403

        # EMPLOYEE should be forbidden
        employee_response = client.delete(
            "/api/timer-cards/999",
            headers={"Authorization": f"Bearer {employee_token}"}
        )
        assert employee_response.status_code == 403

    def test_role_inheritance(self, client, users_with_roles):
        """Test that higher roles have permissions of lower roles."""
        # SUPER_ADMIN should be able to access admin-protected endpoints
        super_admin_login = client.post(
            "/api/auth/login",
            data={"username": "super_admin_user", "password": "test-password"},
        )
        super_admin_token = super_admin_login.json()["access_token"]

        # Try to access admin-only endpoint with SUPER_ADMIN token
        response = client.delete(
            "/api/timer-cards/999",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )

        # Should NOT be forbidden (403)
        # Might be 404 (not found) or 200/204 (success)
        assert response.status_code != 403

    def test_no_token_access_denied(self, client):
        """Test that endpoints requiring authentication deny access without token."""
        # Try to access protected endpoint without token
        response = client.delete("/api/timer-cards/999")

        assert response.status_code == 401

    def test_invalid_token_access_denied(self, client):
        """Test that invalid tokens are rejected."""
        # Try to access protected endpoint with invalid token
        response = client.delete(
            "/api/timer-cards/999",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

        assert response.status_code == 401


# ============================================
# SECURITY INTEGRATION TESTS
# ============================================

class TestSecurityIntegration:
    """Integration tests combining multiple security features."""

    def test_full_authentication_flow(self, client):
        """Test complete auth flow: register → login → refresh → protected endpoint."""
        from app.core.database import SessionLocal

        session = SessionLocal()
        try:
            # 1. Register a new user
            unique_id = int(time.time())
            register_response = client.post(
                "/api/auth/register",
                json={
                    "username": f"integration_user_{unique_id}",
                    "email": f"integration{unique_id}@example.com",
                    "password": "SecurePassword123!",
                    "full_name": "Integration Test User",
                    "role": "ADMIN"  # Admin role for testing protected endpoints
                }
            )
            assert register_response.status_code == 201

            # 2. Login
            login_response = client.post(
                "/api/auth/login",
                data={"username": f"integration_user_{unique_id}", "password": "SecurePassword123!"},
            )
            assert login_response.status_code == 200
            access_token = login_response.json()["access_token"]
            refresh_token = login_response.json()["refresh_token"]

            # 3. Access protected endpoint
            protected_response = client.get(
                "/api/dashboard/stats",  # Dashboard endpoint that should require auth
                headers={"Authorization": f"Bearer {access_token}"}
            )
            # Should succeed (200) or at least not be 401/403
            assert protected_response.status_code in [200, 404]

            # 4. Refresh tokens
            refresh_response = client.post(
                "/api/auth/refresh",
                json={"refresh_token": refresh_token}
            )
            assert refresh_response.status_code == 200
            new_access_token = refresh_response.json()["access_token"]

            # 5. Use new access token
            new_protected_response = client.get(
                "/api/dashboard/stats",
                headers={"Authorization": f"Bearer {new_access_token}"}
            )
            assert new_protected_response.status_code in [200, 404]

            # 6. Logout
            logout_response = client.post(
                "/api/auth/logout",
                json={"refresh_token": refresh_response.json()["refresh_token"]},
                headers={"Authorization": f"Bearer {new_access_token}"}
            )
            assert logout_response.status_code == 200

        finally:
            session.close()
