import pytest
from datetime import datetime, timezone, timedelta

from app.services import ResourceService
from app import models, schemas


class TestResourceService:
    """Test ResourceService business logic"""

    def test_create_resource_success(self, test_db):
        """Test successful resource creation"""
        db = test_db()
        service = ResourceService(db)

        resource_data = schemas.ResourceCreate(
            name="Test Meeting Room", tags=["meeting", "projector"], available=True
        )

        try:
            resource = service.create_resource(resource_data)

            assert resource.id is not None
            assert resource.name == "Test Meeting Room"
            assert resource.tags == ["meeting", "projector"]
            assert resource.available is True
        finally:
            db.close()

    def test_create_resource_duplicate_name(self, test_db):
        """Test creating resource with duplicate name"""
        db = test_db()
        service = ResourceService(db)

        resource_data = schemas.ResourceCreate(
            name="Duplicate Room", tags=["test"], available=True
        )

        try:
            # Create first resource
            service.create_resource(resource_data)

            # Try to create duplicate
            with pytest.raises(ValueError, match="already exists"):
                service.create_resource(resource_data)
        finally:
            db.close()

    def test_search_resources_by_query(self, test_db, test_resource):
        """Test searching resources by text query"""
        db = test_db()
        service = ResourceService(db)

        try:
            # Search by name
            results = service.search_resources(query="conference")
            assert len(results) >= 1
            assert any("conference" in r.name.lower() for r in results)

            # Search by tag
            results = service.search_resources(query="meeting")
            assert len(results) >= 1
            assert any("meeting" in r.tags for r in results)

            # Search with no results
            results = service.search_resources(query="nonexistent")
            assert len(results) == 0
        finally:
            db.close()

    def test_search_resources_by_availability(self, test_db, test_resource):
        """Test searching resources by availability"""
        db = test_db()
        service = ResourceService(db)

        try:
            # Search available only
            available_results = service.search_resources(available_only=True)
            assert all(r.available for r in available_results)

            # Search all resources
            all_results = service.search_resources(available_only=False)
            assert len(all_results) >= len(available_results)
        finally:
            db.close()

    def test_search_resources_with_time_filter(self, test_db, test_resource):
        """Test searching resources with time-based availability"""
        db = test_db()
        service = ResourceService(db)

        try:
            future_start = datetime.now(timezone.utc) + timedelta(days=1)
            future_end = future_start + timedelta(hours=2)

            results = service.search_resources(
                available_from=future_start, available_until=future_end
            )

            # Should find available resources for the future time slot
            assert len(results) >= 1
            assert all(r.available for r in results)
        finally:
            db.close()

    def test_has_conflict(self, test_db, test_resource):
        """Test conflict detection logic"""
        db = test_db()
        service = ResourceService(db)

        try:
            # Create a reservation first
            future_start = datetime.now(timezone.utc) + timedelta(days=1)
            future_end = future_start + timedelta(hours=2)

            reservation = models.Reservation(
                user_id=1,  # Assuming user exists
                resource_id=test_resource.id,
                start_time=future_start,
                end_time=future_end,
                status="active",
            )
            db.add(reservation)
            db.commit()

            # Test conflict detection
            conflict_start = future_start + timedelta(minutes=30)
            conflict_end = future_end + timedelta(minutes=30)

            has_conflict = service._has_conflict(
                test_resource.id, conflict_start, conflict_end
            )
            assert has_conflict is True

            # Test no conflict
            no_conflict_start = future_end + timedelta(hours=1)
            no_conflict_end = no_conflict_start + timedelta(hours=1)

            has_no_conflict = service._has_conflict(
                test_resource.id, no_conflict_start, no_conflict_end
            )
            assert has_no_conflict is False
        finally:
            db.close()
