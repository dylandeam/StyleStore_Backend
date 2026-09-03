"""
Tests for user-related endpoints: /api/v1/users/me, protected route behaviors.
"""
def test_get_me_unauthorized(client):
    """Test accessing protected route without authorization header."""
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401 or response.status_code == 403


def test_get_me_invalid_token(client):
    """Test accessing protected route with malformed JWT."""
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer not-a-valid-token-format"},
    )
    assert response.status_code == 401


def test_get_me_authenticated(client):
    """Test accessing protected route with a valid JWT."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "me@example.com",
            "password": "Password123!",
            "name": "Me Profile",
        },
    )

    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "me@example.com",
            "password": "Password123!",
        },
    )
    token = login_res.json()["access_token"]

    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert data["name"] == "Me Profile"
    assert "id" in data
