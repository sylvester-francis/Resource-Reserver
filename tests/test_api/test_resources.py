from fastapi import status

# API v1 prefix
API_V1 = "/api/v1"


class TestResources:
    """Test resource management endpoints"""

    def test_create_resource_success(self, client, auth_headers):
        """Test successful resource creation"""
        resource_data = {
            "name": "New Meeting Room",
            "tags": ["meeting", "projector"],
            "available": True,
        }

        response = client.post(
            f"{API_V1}/resources", json=resource_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == resource_data["name"]
        assert data["tags"] == resource_data["tags"]
        assert data["available"] == resource_data["available"]
        assert "id" in data

    def test_create_resource_without_auth(self, client):
        """Test resource creation without authentication"""
        resource_data = {
            "name": "Unauthorized Room",
            "tags": ["test"],
            "available": True,
        }

        response = client.post(f"{API_V1}/resources", json=resource_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_resource_invalid_data(self, client, auth_headers):
        """Test resource creation with invalid data"""
        # Empty name
        response = client.post(
            f"{API_V1}/resources",
            json={"name": "", "tags": ["test"], "available": True},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Missing required fields
        response = client.post(
            f"{API_V1}/resources", json={"tags": ["test"]}, headers=auth_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_resources(self, client, test_resource):
        """Test listing all resources"""
        response = client.get(f"{API_V1}/resources")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Check if test resource is in the list
        resource_names = [r["name"] for r in data]
        assert "Test Conference Room" in resource_names

    def test_search_resources_by_query(self, client, test_resource):
        """Test searching resources by query"""
        response = client.get(f"{API_V1}/resources/search?q=conference")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

        # Should find the test resource
        if data:
            assert any(
                "conference" in r["name"].lower()
                or "conference" in [tag.lower() for tag in r["tags"]]
                for r in data
            )

    def test_search_resources_by_availability(self, client, test_resource):
        """Test searching resources by availability"""
        response = client.get(f"{API_V1}/resources/search?available_only=true")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

        # All returned resources should be available
        for resource in data:
            assert resource["available"] is True

    def test_search_resources_with_time_filter(
        self, client, test_resource, future_datetime
    ):
        """Test searching resources with time availability filter"""
        from datetime import timedelta

        start_time = future_datetime
        end_time = start_time + timedelta(hours=2)

        params = {
            "available_from": start_time.isoformat(),
            "available_until": end_time.isoformat(),
        }

        response = client.get(f"{API_V1}/resources/search", params=params)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_search_resources_invalid_time_range(self, client):
        """Test searching with invalid time range"""
        from datetime import datetime, timedelta

        now = datetime.now()
        start_time = now + timedelta(hours=2)
        end_time = now + timedelta(hours=1)  # End before start

        params = {
            "available_from": start_time.isoformat(),
            "available_until": end_time.isoformat(),
        }

        response = client.get(f"{API_V1}/resources/search", params=params)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_resources_csv_success(self, client, auth_headers):
        """Test successful CSV upload"""
        csv_content = """name,tags,available
"Test Room 1","meeting,small",true
"Test Room 2","conference,large",true
"Equipment A","projector,mobile",false
"""

        files = {"file": ("test_resources.csv", csv_content, "text/csv")}

        response = client.post(
            f"{API_V1}/resources/upload", files=files, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "created_count" in data
        assert data["created_count"] > 0
        assert "errors" in data

    def test_upload_resources_csv_invalid_file(self, client, auth_headers):
        """Test CSV upload with invalid file"""
        files = {"file": ("test.txt", "not a csv", "text/plain")}

        response = client.post(
            f"{API_V1}/resources/upload", files=files, headers=auth_headers
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_resources_csv_without_auth(self, client):
        """Test CSV upload without authentication"""
        csv_content = "name,tags,available\nTest Room,meeting,true"
        files = {"file": ("test.csv", csv_content, "text/csv")}

        response = client.post(f"{API_V1}/resources/upload", files=files)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
