"""Unit tests for Label model functionality."""

import pytest
from sqlalchemy.exc import IntegrityError

from app import models


class TestLabelModel:
    """Test Label model behavior."""

    def test_label_creation(self, test_db):
        """Test basic label creation."""
        db = test_db()
        try:
            label = models.Label(
                category="environment",
                value="production",
                color="#10b981",
                description="Production environment resources",
            )
            db.add(label)
            db.commit()
            db.refresh(label)

            assert label.id is not None
            assert label.category == "environment"
            assert label.value == "production"
            assert label.color == "#10b981"
            assert label.description == "Production environment resources"
            assert label.created_at is not None
        finally:
            db.close()

    def test_label_default_color(self, test_db):
        """Test label uses default color when not specified."""
        db = test_db()
        try:
            label = models.Label(
                category="team",
                value="engineering",
            )
            db.add(label)
            db.commit()
            db.refresh(label)

            assert label.color == "#6366f1"
        finally:
            db.close()

    def test_label_full_name_property(self, test_db):
        """Test the full_name computed property."""
        db = test_db()
        try:
            label = models.Label(
                category="environment",
                value="staging",
            )
            db.add(label)
            db.commit()
            db.refresh(label)

            assert label.full_name == "environment:staging"
        finally:
            db.close()

    def test_label_unique_constraint(self, test_db):
        """Test unique constraint on category + value."""
        db = test_db()
        try:
            label1 = models.Label(
                category="environment",
                value="production",
            )
            db.add(label1)
            db.commit()

            # Try to create duplicate
            label2 = models.Label(
                category="environment",
                value="production",
            )
            db.add(label2)

            with pytest.raises(IntegrityError):
                db.commit()
        finally:
            db.rollback()
            db.close()

    def test_label_same_value_different_category(self, test_db):
        """Test same value is allowed in different categories."""
        db = test_db()
        try:
            label1 = models.Label(
                category="environment",
                value="alpha",
            )
            label2 = models.Label(
                category="team",
                value="alpha",
            )
            db.add_all([label1, label2])
            db.commit()

            assert label1.id != label2.id
            assert label1.value == label2.value
            assert label1.category != label2.category
        finally:
            db.close()


class TestResourceLabelModel:
    """Test ResourceLabel association model behavior."""

    def test_resource_label_creation(self, test_db, test_resource):
        """Test creating a resource-label association."""
        db = test_db()
        try:
            label = models.Label(
                category="type",
                value="conference",
            )
            db.add(label)
            db.commit()
            db.refresh(label)

            resource_label = models.ResourceLabel(
                resource_id=test_resource.id,
                label_id=label.id,
            )
            db.add(resource_label)
            db.commit()
            db.refresh(resource_label)

            assert resource_label.id is not None
            assert resource_label.resource_id == test_resource.id
            assert resource_label.label_id == label.id
            assert resource_label.created_at is not None
        finally:
            db.close()

    def test_resource_label_unique_constraint(self, test_db, test_resource):
        """Test unique constraint prevents duplicate assignments."""
        db = test_db()
        try:
            label = models.Label(
                category="type",
                value="meeting",
            )
            db.add(label)
            db.commit()
            db.refresh(label)

            # First assignment
            rl1 = models.ResourceLabel(
                resource_id=test_resource.id,
                label_id=label.id,
            )
            db.add(rl1)
            db.commit()

            # Duplicate assignment
            rl2 = models.ResourceLabel(
                resource_id=test_resource.id,
                label_id=label.id,
            )
            db.add(rl2)

            with pytest.raises(IntegrityError):
                db.commit()
        finally:
            db.rollback()
            db.close()

    def test_label_cascade_delete(self, test_db, test_resource):
        """Test that deleting a label cascades to resource_labels."""
        db = test_db()
        try:
            label = models.Label(
                category="status",
                value="active",
            )
            db.add(label)
            db.commit()
            db.refresh(label)

            resource_label = models.ResourceLabel(
                resource_id=test_resource.id,
                label_id=label.id,
            )
            db.add(resource_label)
            db.commit()
            resource_label_id = resource_label.id

            # Delete label
            db.delete(label)
            db.commit()

            # Verify resource_label is also deleted
            remaining = (
                db.query(models.ResourceLabel)
                .filter(models.ResourceLabel.id == resource_label_id)
                .first()
            )
            assert remaining is None
        finally:
            db.close()

    def test_resource_cascade_delete_labels(self, test_db):
        """Test that deleting a resource cascades to resource_labels."""
        db = test_db()
        try:
            # Create a separate resource for this test
            resource = models.Resource(
                name="Test Resource For Cascade",
                available=True,
            )
            db.add(resource)
            db.commit()
            db.refresh(resource)

            label = models.Label(
                category="location",
                value="building-a",
            )
            db.add(label)
            db.commit()
            db.refresh(label)

            resource_label = models.ResourceLabel(
                resource_id=resource.id,
                label_id=label.id,
            )
            db.add(resource_label)
            db.commit()
            resource_label_id = resource_label.id

            # Delete resource
            db.delete(resource)
            db.commit()

            # Verify resource_label is also deleted
            remaining = (
                db.query(models.ResourceLabel)
                .filter(models.ResourceLabel.id == resource_label_id)
                .first()
            )
            assert remaining is None

            # Verify label still exists
            label_still_exists = (
                db.query(models.Label).filter(models.Label.id == label.id).first()
            )
            assert label_still_exists is not None
        finally:
            db.close()


class TestLabelRelationships:
    """Test Label-Resource many-to-many relationships."""

    def test_resource_multiple_labels(self, test_db):
        """Test assigning multiple labels to a single resource."""
        db = test_db()
        try:
            # Create a resource within this session
            resource = models.Resource(
                name="Multi-label Resource",
                available=True,
            )
            db.add(resource)
            db.commit()
            db.refresh(resource)

            labels = [
                models.Label(category="environment", value="dev"),
                models.Label(category="team", value="backend"),
                models.Label(category="type", value="api-server"),
            ]
            db.add_all(labels)
            db.commit()

            for label in labels:
                db.refresh(label)
                rl = models.ResourceLabel(
                    resource_id=resource.id,
                    label_id=label.id,
                )
                db.add(rl)
            db.commit()

            # Verify all labels are assigned
            db.refresh(resource)
            assert len(resource.resource_labels) == 3
        finally:
            db.close()

    def test_label_multiple_resources(self, test_db):
        """Test assigning a single label to multiple resources."""
        db = test_db()
        try:
            label = models.Label(category="shared", value="common")
            db.add(label)
            db.commit()
            db.refresh(label)

            resources = [
                models.Resource(name="Resource A", available=True),
                models.Resource(name="Resource B", available=True),
                models.Resource(name="Resource C", available=True),
            ]
            db.add_all(resources)
            db.commit()

            for resource in resources:
                db.refresh(resource)
                rl = models.ResourceLabel(
                    resource_id=resource.id,
                    label_id=label.id,
                )
                db.add(rl)
            db.commit()

            # Verify all resources have the label
            db.refresh(label)
            assert len(label.resource_labels) == 3
        finally:
            db.close()
