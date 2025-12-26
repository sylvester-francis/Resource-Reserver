"""Tests for resource groups functionality.

Author: Sylvester-Francis
"""

from fastapi.testclient import TestClient


class TestResourceGroupModels:
    """Tests for resource group models."""

    def test_resource_group_model(self, test_db):
        """Test ResourceGroup model creation."""
        from app import models

        db = test_db()

        group = models.ResourceGroup(
            name="Conference Rooms",
            description="All conference rooms",
            building="Main Building",
            floor="1st Floor",
        )
        db.add(group)
        db.commit()
        db.refresh(group)

        assert group.id is not None
        assert group.name == "Conference Rooms"
        assert group.building == "Main Building"
        assert group.created_at is not None

        db.close()

    def test_resource_group_hierarchy(self, test_db):
        """Test ResourceGroup parent-child relationship."""
        from app import models

        db = test_db()

        parent = models.ResourceGroup(name="All Rooms", building="HQ")
        db.add(parent)
        db.commit()
        db.refresh(parent)

        child = models.ResourceGroup(
            name="Conference Rooms",
            parent_id=parent.id,
            building="HQ",
        )
        db.add(child)
        db.commit()
        db.refresh(child)

        assert child.parent_id == parent.id
        assert child.parent.name == "All Rooms"

        db.close()

    def test_resource_in_group(self, test_db):
        """Test Resource group assignment."""
        from app import models

        db = test_db()

        group = models.ResourceGroup(name="Test Group")
        db.add(group)
        db.commit()
        db.refresh(group)

        resource = models.Resource(
            name="Test Resource",
            group_id=group.id,
        )
        db.add(resource)
        db.commit()
        db.refresh(resource)

        assert resource.group_id == group.id
        assert resource.group.name == "Test Group"
        assert len(group.resources) == 1

        db.close()

    def test_resource_parent_child(self, test_db):
        """Test Resource parent-child relationship."""
        from app import models

        db = test_db()

        parent = models.Resource(name="Conference Room A")
        db.add(parent)
        db.commit()
        db.refresh(parent)

        child = models.Resource(
            name="Projector A",
            parent_id=parent.id,
        )
        db.add(child)
        db.commit()
        db.refresh(child)

        assert child.parent_id == parent.id
        assert child.parent.name == "Conference Room A"
        assert len(parent.children) == 1

        db.close()


class TestResourceGroupEndpoints:
    """Tests for resource group API endpoints."""

    def test_create_resource_group(self, client: TestClient, admin_headers: dict):
        """Test creating a resource group."""
        response = client.post(
            "/api/v1/resource-groups/",
            headers=admin_headers,
            json={
                "name": "Test Group",
                "description": "A test group",
                "building": "Building A",
                "floor": "1st",
                "room": "101",
            },
        )
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "Test Group"
        assert data["building"] == "Building A"
        assert data["id"] is not None

    def test_create_resource_group_non_admin(
        self, client: TestClient, auth_headers: dict
    ):
        """Test non-admin cannot create resource group."""
        response = client.post(
            "/api/v1/resource-groups/",
            headers=auth_headers,
            json={"name": "Test Group"},
        )
        assert response.status_code == 403

    def test_create_nested_group(self, client: TestClient, admin_headers: dict):
        """Test creating a nested resource group."""
        # Create parent
        parent_response = client.post(
            "/api/v1/resource-groups/",
            headers=admin_headers,
            json={"name": "Parent Group"},
        )
        parent_id = parent_response.json()["id"]

        # Create child
        child_response = client.post(
            "/api/v1/resource-groups/",
            headers=admin_headers,
            json={
                "name": "Child Group",
                "parent_id": parent_id,
            },
        )
        assert child_response.status_code == 201
        assert child_response.json()["parent_id"] == parent_id

    def test_list_resource_groups(
        self, client: TestClient, admin_headers: dict, auth_headers: dict
    ):
        """Test listing resource groups."""
        # Create a group first
        client.post(
            "/api/v1/resource-groups/",
            headers=admin_headers,
            json={"name": "List Test Group"},
        )

        # List groups
        response = client.get("/api/v1/resource-groups/", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_resource_group(
        self, client: TestClient, admin_headers: dict, auth_headers: dict
    ):
        """Test getting a specific resource group."""
        # Create
        create_response = client.post(
            "/api/v1/resource-groups/",
            headers=admin_headers,
            json={"name": "Get Test Group"},
        )
        group_id = create_response.json()["id"]

        # Get
        response = client.get(
            f"/api/v1/resource-groups/{group_id}", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Get Test Group"

    def test_get_resource_group_not_found(self, client: TestClient, auth_headers: dict):
        """Test getting non-existent resource group."""
        response = client.get("/api/v1/resource-groups/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_update_resource_group(self, client: TestClient, admin_headers: dict):
        """Test updating a resource group."""
        # Create
        create_response = client.post(
            "/api/v1/resource-groups/",
            headers=admin_headers,
            json={"name": "Original Name"},
        )
        group_id = create_response.json()["id"]

        # Update
        response = client.patch(
            f"/api/v1/resource-groups/{group_id}",
            headers=admin_headers,
            json={"name": "Updated Name", "building": "New Building"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"
        assert response.json()["building"] == "New Building"

    def test_update_group_circular_parent(
        self, client: TestClient, admin_headers: dict
    ):
        """Test preventing circular parent reference."""
        # Create parent
        parent_response = client.post(
            "/api/v1/resource-groups/",
            headers=admin_headers,
            json={"name": "Parent"},
        )
        parent_id = parent_response.json()["id"]

        # Create child
        child_response = client.post(
            "/api/v1/resource-groups/",
            headers=admin_headers,
            json={"name": "Child", "parent_id": parent_id},
        )
        child_id = child_response.json()["id"]

        # Try to set parent's parent to child (circular)
        response = client.patch(
            f"/api/v1/resource-groups/{parent_id}",
            headers=admin_headers,
            json={"parent_id": child_id},
        )
        assert response.status_code == 400
        assert "Circular" in response.json()["detail"]

    def test_delete_resource_group(self, client: TestClient, admin_headers: dict):
        """Test deleting a resource group."""
        # Create
        create_response = client.post(
            "/api/v1/resource-groups/",
            headers=admin_headers,
            json={"name": "Delete Test Group"},
        )
        group_id = create_response.json()["id"]

        # Delete
        response = client.delete(
            f"/api/v1/resource-groups/{group_id}",
            headers=admin_headers,
        )
        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(
            f"/api/v1/resource-groups/{group_id}",
            headers=admin_headers,
        )
        assert get_response.status_code == 404

    def test_delete_group_with_children_fails(
        self, client: TestClient, admin_headers: dict
    ):
        """Test deleting group with children without cascade fails."""
        # Create parent
        parent_response = client.post(
            "/api/v1/resource-groups/",
            headers=admin_headers,
            json={"name": "Parent With Children"},
        )
        parent_id = parent_response.json()["id"]

        # Create child
        client.post(
            "/api/v1/resource-groups/",
            headers=admin_headers,
            json={"name": "Child", "parent_id": parent_id},
        )

        # Try to delete parent without cascade
        response = client.delete(
            f"/api/v1/resource-groups/{parent_id}",
            headers=admin_headers,
        )
        assert response.status_code == 400
        assert "child group" in response.json()["detail"]

    def test_delete_group_cascade(self, client: TestClient, admin_headers: dict):
        """Test deleting group with cascade."""
        # Create parent
        parent_response = client.post(
            "/api/v1/resource-groups/",
            headers=admin_headers,
            json={"name": "Parent To Cascade Delete"},
        )
        parent_id = parent_response.json()["id"]

        # Create child
        client.post(
            "/api/v1/resource-groups/",
            headers=admin_headers,
            json={"name": "Child To Delete", "parent_id": parent_id},
        )

        # Delete with cascade
        response = client.delete(
            f"/api/v1/resource-groups/{parent_id}?cascade=true",
            headers=admin_headers,
        )
        assert response.status_code == 204

    def test_get_resource_group_tree(
        self, client: TestClient, admin_headers: dict, auth_headers: dict
    ):
        """Test getting the resource group tree."""
        # Create some groups
        client.post(
            "/api/v1/resource-groups/",
            headers=admin_headers,
            json={"name": "Tree Root"},
        )

        response = client.get("/api/v1/resource-groups/tree", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "groups" in data
        assert "total_groups" in data
        assert "total_resources" in data

    def test_list_buildings(
        self, client: TestClient, admin_headers: dict, auth_headers: dict
    ):
        """Test listing unique buildings."""
        # Create groups with buildings
        client.post(
            "/api/v1/resource-groups/",
            headers=admin_headers,
            json={"name": "Group A", "building": "Building Alpha"},
        )
        client.post(
            "/api/v1/resource-groups/",
            headers=admin_headers,
            json={"name": "Group B", "building": "Building Beta"},
        )

        response = client.get("/api/v1/resource-groups/buildings", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "buildings" in data
        assert "Building Alpha" in data["buildings"]
        assert "Building Beta" in data["buildings"]


class TestResourceAssignment:
    """Tests for resource group assignment."""

    def test_list_resources_in_group(
        self, client: TestClient, admin_headers: dict, auth_headers: dict
    ):
        """Test listing resources in a group."""
        # Create group
        group_response = client.post(
            "/api/v1/resource-groups/",
            headers=admin_headers,
            json={"name": "Resources Group"},
        )
        group_id = group_response.json()["id"]

        response = client.get(
            f"/api/v1/resource-groups/{group_id}/resources",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_assign_resource_to_group(self, client: TestClient, admin_headers: dict):
        """Test assigning a resource to a group."""
        # Create group
        group_response = client.post(
            "/api/v1/resource-groups/",
            headers=admin_headers,
            json={"name": "Assignment Group"},
        )
        group_id = group_response.json()["id"]

        # Create resource
        resource_response = client.post(
            "/api/v1/resources/",
            headers=admin_headers,
            json={"name": "Resource To Assign"},
        )
        resource_id = resource_response.json()["id"]

        # Assign
        response = client.post(
            f"/api/v1/resource-groups/{group_id}/resources",
            headers=admin_headers,
            json={"resource_id": resource_id},
        )
        assert response.status_code == 200
        assert "assigned" in response.json()["message"]

    def test_remove_resource_from_group(self, client: TestClient, admin_headers: dict):
        """Test removing a resource from a group."""
        # Create group
        group_response = client.post(
            "/api/v1/resource-groups/",
            headers=admin_headers,
            json={"name": "Remove Test Group"},
        )
        group_id = group_response.json()["id"]

        # Create resource
        resource_response = client.post(
            "/api/v1/resources/",
            headers=admin_headers,
            json={"name": "Resource To Remove"},
        )
        resource_id = resource_response.json()["id"]

        # Assign first
        client.post(
            f"/api/v1/resource-groups/{group_id}/resources",
            headers=admin_headers,
            json={"resource_id": resource_id},
        )

        # Remove
        response = client.delete(
            f"/api/v1/resource-groups/{group_id}/resources/{resource_id}",
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert "removed" in response.json()["message"]

    def test_list_ungrouped_resources(self, client: TestClient, auth_headers: dict):
        """Test listing ungrouped resources."""
        response = client.get(
            "/api/v1/resource-groups/ungrouped",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestResourceHierarchy:
    """Tests for resource parent-child hierarchy."""

    def test_set_resource_parent(self, client: TestClient, admin_headers: dict):
        """Test setting resource parent."""
        # Create parent resource
        parent_response = client.post(
            "/api/v1/resources/",
            headers=admin_headers,
            json={"name": "Parent Resource"},
        )
        parent_id = parent_response.json()["id"]

        # Create child resource
        child_response = client.post(
            "/api/v1/resources/",
            headers=admin_headers,
            json={"name": "Child Resource"},
        )
        child_id = child_response.json()["id"]

        # Set parent
        response = client.post(
            "/api/v1/resource-groups/resources/set-parent",
            headers=admin_headers,
            json={"resource_id": child_id, "parent_id": parent_id},
        )
        assert response.status_code == 200
        assert "parent set" in response.json()["message"]

    def test_set_resource_parent_circular(
        self, client: TestClient, admin_headers: dict
    ):
        """Test preventing circular resource parent."""
        # Create resources
        parent_response = client.post(
            "/api/v1/resources/",
            headers=admin_headers,
            json={"name": "Circular Parent"},
        )
        parent_id = parent_response.json()["id"]

        child_response = client.post(
            "/api/v1/resources/",
            headers=admin_headers,
            json={"name": "Circular Child"},
        )
        child_id = child_response.json()["id"]

        # Set parent -> child relationship
        client.post(
            "/api/v1/resource-groups/resources/set-parent",
            headers=admin_headers,
            json={"resource_id": child_id, "parent_id": parent_id},
        )

        # Try to set child as parent of parent (circular)
        response = client.post(
            "/api/v1/resource-groups/resources/set-parent",
            headers=admin_headers,
            json={"resource_id": parent_id, "parent_id": child_id},
        )
        assert response.status_code == 400
        assert "Circular" in response.json()["detail"]

    def test_get_resource_children(
        self, client: TestClient, admin_headers: dict, auth_headers: dict
    ):
        """Test getting resource children."""
        # Create parent
        parent_response = client.post(
            "/api/v1/resources/",
            headers=admin_headers,
            json={"name": "Children Parent"},
        )
        parent_id = parent_response.json()["id"]

        # Create child
        child_response = client.post(
            "/api/v1/resources/",
            headers=admin_headers,
            json={"name": "Child 1"},
        )
        child_id = child_response.json()["id"]

        # Set parent
        client.post(
            "/api/v1/resource-groups/resources/set-parent",
            headers=admin_headers,
            json={"resource_id": child_id, "parent_id": parent_id},
        )

        # Get children
        response = client.get(
            f"/api/v1/resource-groups/resources/{parent_id}/children",
            headers=auth_headers,
        )
        assert response.status_code == 200
        children = response.json()
        assert len(children) >= 1
        assert any(c["name"] == "Child 1" for c in children)

    def test_remove_resource_parent(self, client: TestClient, admin_headers: dict):
        """Test removing resource parent."""
        # Create resources
        parent_response = client.post(
            "/api/v1/resources/",
            headers=admin_headers,
            json={"name": "Remove Parent"},
        )
        parent_id = parent_response.json()["id"]

        child_response = client.post(
            "/api/v1/resources/",
            headers=admin_headers,
            json={"name": "Remove Child"},
        )
        child_id = child_response.json()["id"]

        # Set parent
        client.post(
            "/api/v1/resource-groups/resources/set-parent",
            headers=admin_headers,
            json={"resource_id": child_id, "parent_id": parent_id},
        )

        # Remove parent
        response = client.post(
            "/api/v1/resource-groups/resources/set-parent",
            headers=admin_headers,
            json={"resource_id": child_id, "parent_id": None},
        )
        assert response.status_code == 200
        assert "parent removed" in response.json()["message"]
