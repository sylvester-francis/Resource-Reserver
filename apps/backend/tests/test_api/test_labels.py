"""API tests for label endpoints."""

from fastapi import status

# API v1 prefix
API_V1 = "/api/v1"


class TestLabelEndpoints:
    """Test label CRUD endpoints."""

    def test_create_label_success(self, client, admin_headers):
        """Test successful label creation by admin."""
        response = client.post(
            f"{API_V1}/labels",
            json={
                "category": "environment",
                "value": "production",
                "color": "#10b981",
                "description": "Production environment",
            },
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["category"] == "environment"
        assert data["value"] == "production"
        assert data["color"] == "#10b981"
        assert data["description"] == "Production environment"
        assert data["full_name"] == "environment:production"
        assert data["resource_count"] == 0
        assert "id" in data

    def test_create_label_default_color(self, client, admin_headers):
        """Test label creation uses default color."""
        response = client.post(
            f"{API_V1}/labels",
            json={
                "category": "team",
                "value": "engineering",
            },
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["color"] == "#6366f1"

    def test_create_label_duplicate_fails(self, client, admin_headers):
        """Test creating duplicate label fails."""
        # Create first label
        client.post(
            f"{API_V1}/labels",
            json={"category": "env", "value": "dev"},
            headers=admin_headers,
        )

        # Try to create duplicate
        response = client.post(
            f"{API_V1}/labels",
            json={"category": "env", "value": "dev"},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"]

    def test_create_label_non_admin_fails(self, client, auth_headers):
        """Test non-admin cannot create labels."""
        response = client.post(
            f"{API_V1}/labels",
            json={"category": "test", "value": "label"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_label_unauthenticated_fails(self, client):
        """Test unauthenticated request fails."""
        response = client.post(
            f"{API_V1}/labels",
            json={"category": "test", "value": "label"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_label_invalid_color_fails(self, client, admin_headers):
        """Test invalid color format fails validation."""
        response = client.post(
            f"{API_V1}/labels",
            json={
                "category": "test",
                "value": "label",
                "color": "invalid",
            },
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_labels_pagination(self, client, admin_headers):
        """Test label listing with pagination."""
        # Create multiple labels
        for i in range(5):
            client.post(
                f"{API_V1}/labels",
                json={"category": "test", "value": f"label{i}"},
                headers=admin_headers,
            )

        # Get first page
        response = client.get(
            f"{API_V1}/labels",
            params={"limit": 2},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) == 2
        assert data["has_more"] is True
        assert data["next_cursor"] is not None

        # Get next page
        response = client.get(
            f"{API_V1}/labels",
            params={"limit": 2, "cursor": data["next_cursor"]},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data2 = response.json()
        assert len(data2["data"]) == 2

        # Verify no duplicate IDs
        ids1 = {item["id"] for item in data["data"]}
        ids2 = {item["id"] for item in data2["data"]}
        assert ids1.isdisjoint(ids2)

    def test_list_labels_filter_by_category(self, client, admin_headers):
        """Test filtering labels by category."""
        # Create labels in different categories
        client.post(
            f"{API_V1}/labels",
            json={"category": "env", "value": "prod"},
            headers=admin_headers,
        )
        client.post(
            f"{API_V1}/labels",
            json={"category": "env", "value": "staging"},
            headers=admin_headers,
        )
        client.post(
            f"{API_V1}/labels",
            json={"category": "team", "value": "backend"},
            headers=admin_headers,
        )

        # Filter by env category
        response = client.get(
            f"{API_V1}/labels",
            params={"category": "env"},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(label["category"] == "env" for label in data["data"])
        assert len(data["data"]) == 2

    def test_list_labels_search(self, client, admin_headers):
        """Test searching labels."""
        # Create labels
        client.post(
            f"{API_V1}/labels",
            json={"category": "environment", "value": "production"},
            headers=admin_headers,
        )
        client.post(
            f"{API_V1}/labels",
            json={"category": "environment", "value": "development"},
            headers=admin_headers,
        )
        client.post(
            f"{API_V1}/labels",
            json={"category": "team", "value": "frontend"},
            headers=admin_headers,
        )

        # Search for "prod"
        response = client.get(
            f"{API_V1}/labels",
            params={"search": "prod"},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["value"] == "production"

    def test_get_label_success(self, client, admin_headers):
        """Test getting a specific label."""
        # Create label
        create_response = client.post(
            f"{API_V1}/labels",
            json={"category": "type", "value": "server"},
            headers=admin_headers,
        )
        label_id = create_response.json()["id"]

        # Get label
        response = client.get(
            f"{API_V1}/labels/{label_id}",
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == label_id
        assert data["category"] == "type"
        assert data["value"] == "server"

    def test_get_label_not_found(self, client, admin_headers):
        """Test getting non-existent label."""
        response = client.get(
            f"{API_V1}/labels/99999",
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_label_success(self, client, admin_headers):
        """Test updating a label."""
        # Create label
        create_response = client.post(
            f"{API_V1}/labels",
            json={"category": "status", "value": "old-value"},
            headers=admin_headers,
        )
        label_id = create_response.json()["id"]

        # Update label
        response = client.put(
            f"{API_V1}/labels/{label_id}",
            json={
                "value": "new-value",
                "color": "#ef4444",
                "description": "Updated description",
            },
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["value"] == "new-value"
        assert data["color"] == "#ef4444"
        assert data["description"] == "Updated description"
        assert data["category"] == "status"  # Unchanged

    def test_update_label_not_found(self, client, admin_headers):
        """Test updating non-existent label."""
        response = client.put(
            f"{API_V1}/labels/99999",
            json={"value": "new-value"},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_label_duplicate_fails(self, client, admin_headers):
        """Test updating label to duplicate category/value fails."""
        # Create two labels
        client.post(
            f"{API_V1}/labels",
            json={"category": "env", "value": "prod"},
            headers=admin_headers,
        )
        create_response = client.post(
            f"{API_V1}/labels",
            json={"category": "env", "value": "staging"},
            headers=admin_headers,
        )
        label_id = create_response.json()["id"]

        # Try to update to duplicate
        response = client.put(
            f"{API_V1}/labels/{label_id}",
            json={"value": "prod"},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_update_label_non_admin_fails(self, client, admin_headers, auth_headers):
        """Test non-admin cannot update labels."""
        # Create label as admin
        create_response = client.post(
            f"{API_V1}/labels",
            json={"category": "test", "value": "label"},
            headers=admin_headers,
        )
        label_id = create_response.json()["id"]

        # Try to update as non-admin
        response = client.put(
            f"{API_V1}/labels/{label_id}",
            json={"value": "updated"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_label_success(self, client, admin_headers):
        """Test deleting a label."""
        # Create label
        create_response = client.post(
            f"{API_V1}/labels",
            json={"category": "to-delete", "value": "label"},
            headers=admin_headers,
        )
        label_id = create_response.json()["id"]

        # Delete label
        response = client.delete(
            f"{API_V1}/labels/{label_id}",
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert "deleted" in response.json()["message"].lower()

        # Verify label is gone
        get_response = client.get(
            f"{API_V1}/labels/{label_id}",
            headers=admin_headers,
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_label_not_found(self, client, admin_headers):
        """Test deleting non-existent label."""
        response = client.delete(
            f"{API_V1}/labels/99999",
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_label_non_admin_fails(self, client, admin_headers, auth_headers):
        """Test non-admin cannot delete labels."""
        # Create label as admin
        create_response = client.post(
            f"{API_V1}/labels",
            json={"category": "protected", "value": "label"},
            headers=admin_headers,
        )
        label_id = create_response.json()["id"]

        # Try to delete as non-admin
        response = client.delete(
            f"{API_V1}/labels/{label_id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestLabelCategories:
    """Test label category endpoints."""

    def test_list_categories(self, client, admin_headers):
        """Test listing label categories."""
        # Create labels in different categories
        client.post(
            f"{API_V1}/labels",
            json={"category": "environment", "value": "prod"},
            headers=admin_headers,
        )
        client.post(
            f"{API_V1}/labels",
            json={"category": "environment", "value": "staging"},
            headers=admin_headers,
        )
        client.post(
            f"{API_V1}/labels",
            json={"category": "team", "value": "backend"},
            headers=admin_headers,
        )

        response = client.get(
            f"{API_V1}/labels/categories",
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        categories = {cat["category"]: cat["label_count"] for cat in data}
        assert "environment" in categories
        assert categories["environment"] == 2
        assert "team" in categories
        assert categories["team"] == 1


class TestLabelMerge:
    """Test label merging functionality."""

    def test_merge_labels_success(self, client, admin_headers, test_db, test_resource):
        """Test merging multiple labels into one."""
        # Create labels
        label1 = client.post(
            f"{API_V1}/labels",
            json={"category": "type", "value": "old1"},
            headers=admin_headers,
        ).json()
        label2 = client.post(
            f"{API_V1}/labels",
            json={"category": "type", "value": "old2"},
            headers=admin_headers,
        ).json()
        target = client.post(
            f"{API_V1}/labels",
            json={"category": "type", "value": "target"},
            headers=admin_headers,
        ).json()

        # Assign source labels to resource
        client.put(
            f"{API_V1}/labels/resources/{test_resource.id}",
            json={"label_ids": [label1["id"], label2["id"]]},
            headers=admin_headers,
        )

        # Merge labels
        response = client.post(
            f"{API_V1}/labels/merge",
            json={
                "source_label_ids": [label1["id"], label2["id"]],
                "target_label_id": target["id"],
            },
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == target["id"]
        assert data["resource_count"] == 1  # Resource now has target label

        # Verify source labels are deleted
        assert (
            client.get(
                f"{API_V1}/labels/{label1['id']}", headers=admin_headers
            ).status_code
            == status.HTTP_404_NOT_FOUND
        )
        assert (
            client.get(
                f"{API_V1}/labels/{label2['id']}", headers=admin_headers
            ).status_code
            == status.HTTP_404_NOT_FOUND
        )

    def test_merge_labels_different_category_fails(self, client, admin_headers):
        """Test merging labels from different categories fails."""
        label1 = client.post(
            f"{API_V1}/labels",
            json={"category": "env", "value": "source"},
            headers=admin_headers,
        ).json()
        target = client.post(
            f"{API_V1}/labels",
            json={"category": "team", "value": "target"},
            headers=admin_headers,
        ).json()

        response = client.post(
            f"{API_V1}/labels/merge",
            json={
                "source_label_ids": [label1["id"]],
                "target_label_id": target["id"],
            },
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "same category" in response.json()["detail"]

    def test_merge_labels_target_in_source_fails(self, client, admin_headers):
        """Test merging when target is in source list fails."""
        label1 = client.post(
            f"{API_V1}/labels",
            json={"category": "type", "value": "label1"},
            headers=admin_headers,
        ).json()

        response = client.post(
            f"{API_V1}/labels/merge",
            json={
                "source_label_ids": [label1["id"]],
                "target_label_id": label1["id"],
            },
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "cannot be in source" in response.json()["detail"].lower()

    def test_merge_labels_source_not_found(self, client, admin_headers):
        """Test merging with non-existent source label."""
        target = client.post(
            f"{API_V1}/labels",
            json={"category": "type", "value": "target"},
            headers=admin_headers,
        ).json()

        response = client.post(
            f"{API_V1}/labels/merge",
            json={
                "source_label_ids": [99999],
                "target_label_id": target["id"],
            },
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_merge_labels_target_not_found(self, client, admin_headers):
        """Test merging with non-existent target label."""
        label1 = client.post(
            f"{API_V1}/labels",
            json={"category": "type", "value": "source"},
            headers=admin_headers,
        ).json()

        response = client.post(
            f"{API_V1}/labels/merge",
            json={
                "source_label_ids": [label1["id"]],
                "target_label_id": 99999,
            },
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestResourceLabels:
    """Test resource-label assignment endpoints."""

    def test_assign_labels_to_resource(self, client, admin_headers, test_resource):
        """Test assigning labels to a resource."""
        # Create labels
        label1 = client.post(
            f"{API_V1}/labels",
            json={"category": "env", "value": "dev"},
            headers=admin_headers,
        ).json()
        label2 = client.post(
            f"{API_V1}/labels",
            json={"category": "team", "value": "backend"},
            headers=admin_headers,
        ).json()

        # Assign labels
        response = client.put(
            f"{API_V1}/labels/resources/{test_resource.id}",
            json={"label_ids": [label1["id"], label2["id"]]},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        label_ids = {label["id"] for label in data}
        assert label1["id"] in label_ids
        assert label2["id"] in label_ids

    def test_assign_labels_replaces_existing(
        self, client, admin_headers, test_resource
    ):
        """Test assigning labels replaces existing assignments."""
        # Create labels
        label1 = client.post(
            f"{API_V1}/labels",
            json={"category": "old", "value": "label"},
            headers=admin_headers,
        ).json()
        label2 = client.post(
            f"{API_V1}/labels",
            json={"category": "new", "value": "label"},
            headers=admin_headers,
        ).json()

        # Assign first label
        client.put(
            f"{API_V1}/labels/resources/{test_resource.id}",
            json={"label_ids": [label1["id"]]},
            headers=admin_headers,
        )

        # Replace with second label
        response = client.put(
            f"{API_V1}/labels/resources/{test_resource.id}",
            json={"label_ids": [label2["id"]]},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == label2["id"]

    def test_assign_labels_empty_list_removes_all(
        self, client, admin_headers, test_resource
    ):
        """Test assigning empty list removes all labels."""
        # Create and assign label
        label = client.post(
            f"{API_V1}/labels",
            json={"category": "remove", "value": "me"},
            headers=admin_headers,
        ).json()
        client.put(
            f"{API_V1}/labels/resources/{test_resource.id}",
            json={"label_ids": [label["id"]]},
            headers=admin_headers,
        )

        # Remove all labels
        response = client.put(
            f"{API_V1}/labels/resources/{test_resource.id}",
            json={"label_ids": []},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_assign_labels_resource_not_found(self, client, admin_headers):
        """Test assigning labels to non-existent resource."""
        response = client.put(
            f"{API_V1}/labels/resources/99999",
            json={"label_ids": []},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_assign_labels_invalid_label_id(self, client, admin_headers, test_resource):
        """Test assigning invalid label ID fails."""
        response = client.put(
            f"{API_V1}/labels/resources/{test_resource.id}",
            json={"label_ids": [99999]},
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_assign_labels_non_admin_fails(
        self, client, admin_headers, auth_headers, test_resource
    ):
        """Test non-admin cannot assign labels."""
        label = client.post(
            f"{API_V1}/labels",
            json={"category": "test", "value": "label"},
            headers=admin_headers,
        ).json()

        response = client.put(
            f"{API_V1}/labels/resources/{test_resource.id}",
            json={"label_ids": [label["id"]]},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_resource_labels(self, client, admin_headers, test_resource):
        """Test getting labels assigned to a resource."""
        # Create and assign labels
        label = client.post(
            f"{API_V1}/labels",
            json={"category": "get", "value": "test"},
            headers=admin_headers,
        ).json()
        client.put(
            f"{API_V1}/labels/resources/{test_resource.id}",
            json={"label_ids": [label["id"]]},
            headers=admin_headers,
        )

        # Get labels
        response = client.get(
            f"{API_V1}/labels/resources/{test_resource.id}",
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == label["id"]

    def test_get_resource_labels_resource_not_found(self, client, admin_headers):
        """Test getting labels for non-existent resource."""
        response = client.get(
            f"{API_V1}/labels/resources/99999",
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_label_cascade_resource_labels(
        self, client, admin_headers, test_resource
    ):
        """Test deleting label removes resource-label assignments."""
        # Create and assign label
        label = client.post(
            f"{API_V1}/labels",
            json={"category": "cascade", "value": "test"},
            headers=admin_headers,
        ).json()
        client.put(
            f"{API_V1}/labels/resources/{test_resource.id}",
            json={"label_ids": [label["id"]]},
            headers=admin_headers,
        )

        # Delete label
        client.delete(
            f"{API_V1}/labels/{label['id']}",
            headers=admin_headers,
        )

        # Verify resource has no labels
        response = client.get(
            f"{API_V1}/labels/resources/{test_resource.id}",
            headers=admin_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []
