from fastapi import status



class TestAuthentication:
    """Test authentication endpoints."""
    
    def test_register_success(self, client, db_session):
        """Test successful user registration."""
        user_data = {
            "email": "newuser@example.com",
            "password": "testpassword123",
            "display_name": "newuser"
        }

        response = client.post("/register", json=user_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == user_data["email"]
        assert "id" in data
    
    
    def test_login_success(self, client, db_session):
        """Test successful login."""
        # First register a user
        user_data = {
            "email": "loginuser@example.com",
            "password": "testpassword123",
            "display_name": "loginuser"
        }
        register_response = client.post("/register", json=user_data)
        print("register Response:", register_response)


        response = client.post("/token", data={ "username": user_data["email"],  "password": user_data["password"]})
        print("token Response:", response)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
