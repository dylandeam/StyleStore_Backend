"""
Tests for authentication endpoints: register, login, logout, refresh.
"""
def test_register_user_success(client):
    """Test successful user registration."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "Password123!",
            "name": "Test User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"
    assert "id" in data
    assert "is_active" in data
    assert data["is_active"] is True


def test_register_duplicate_email(client):
    """Test registration failure when email already exists."""
    user_payload = {
        "email": "duplicate@example.com",
        "password": "Password123!",
        "name": "Duplicate User",
    }
    res1 = client.post("/api/v1/auth/register", json=user_payload)
    assert res1.status_code == 201

    res2 = client.post("/api/v1/auth/register", json=user_payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"].lower()


def test_register_invalid_data(client):
    """Test validation errors on bad input."""
    # Short password (<8 chars)
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "badpass@example.com",
            "password": "short",
            "name": "Bad User",
        },
    )
    assert response.status_code == 422

    # Invalid email format
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "Password123!",
            "name": "Bad User",
        },
    )
    assert response.status_code == 422


def test_login_success(client):
    """Test successful login returns access & refresh tokens."""
    # Register first
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "password": "ValidPassword123",
            "name": "Login User",
        },
    )

    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@example.com",
            "password": "ValidPassword123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password(client):
    """Test login failure with wrong password."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrongpass@example.com",
            "password": "CorrectPassword123",
            "name": "User",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "wrongpass@example.com",
            "password": "IncorrectPassword123",
        },
    )
    assert response.status_code == 401


def test_logout_and_blacklist(client):
    """Test token revocation during logout."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "logout@example.com",
            "password": "Password123!",
            "name": "Logout User",
        },
    )

    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "logout@example.com",
            "password": "Password123!",
        },
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify token works for /me
    me_res = client.get("/api/v1/users/me", headers=headers)
    assert me_res.status_code == 200

    # Logout
    logout_res = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 200
    assert "logged out" in logout_res.json()["message"].lower()

    # Verify token is now blacklisted and rejected
    me_after_logout = client.get("/api/v1/users/me", headers=headers)
    assert me_after_logout.status_code == 401


def test_refresh_token(client):
    """Test obtaining a new access token via refresh token."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh@example.com",
            "password": "Password123!",
            "name": "Refresh User",
        },
    )

    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "refresh@example.com",
            "password": "Password123!",
        },
    )
    refresh_token = login_res.json()["refresh_token"]

    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    data = refresh_res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
