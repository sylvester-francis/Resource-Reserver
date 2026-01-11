# Resource-Reserver Enhancement Plan

## Overview
This document outlines the implementation plan for three major enhancements to the Resource-Reserver system:
1. Enterprise OAuth2 Authentication & Authorization Guide
2. Admin-Level Label/Tag Management System
3. Automated Testing Integration with Squatter Detection

---

## 1. Enterprise OAuth2 Authentication & Authorization Guide

### Objective
Create comprehensive, step-by-step documentation for enterprise authentication and authorization, focusing on OAuth2/OIDC integration with common enterprise identity providers.

### Current State Analysis
- ✅ JWT token system with refresh tokens already implemented
- ✅ RBAC with Casbin for fine-grained access control
- ✅ MFA support (TOTP) available
- ✅ OAuth2 client management API exists (`/apps/backend/app/routers/oauth.py`)
- ⚠️  Missing: Comprehensive enterprise integration documentation
- ⚠️  Missing: Provider-specific setup guides (Okta, Azure AD, Google Workspace, etc.)

### Implementation Plan

#### 1.1 Documentation Structure
Create `/docs/enterprise/` directory with the following guides:

**a) Overview Document** (`authentication-overview.md`)
- Authentication vs Authorization explained
- System architecture diagram
- Token flow diagrams (access + refresh tokens)
- Security best practices

**b) OAuth2/OIDC Integration Guide** (`oauth2-integration.md`)
- OAuth2 grant types supported
- OIDC (OpenID Connect) flow explanation
- Token validation and claims mapping
- Role synchronization from IdP

**c) Provider-Specific Guides**
- `okta-integration.md` - Okta SSO setup
- `azure-ad-integration.md` - Microsoft Azure AD / Entra ID
- `google-workspace-integration.md` - Google Workspace
- `auth0-integration.md` - Auth0 integration
- `keycloak-integration.md` - Self-hosted Keycloak

**d) Enterprise Features** (`enterprise-auth-features.md`)
- SCIM provisioning for user/group sync
- SAML 2.0 support (if needed)
- Just-In-Time (JIT) provisioning
- Group-based role assignment
- Automated deprovisioning

**e) Security & Compliance** (`security-compliance.md`)
- Token security best practices
- Session management
- Audit logging for compliance (SOC2, ISO 27001)
- MFA enforcement policies
- Password policies and rotation
- IP allowlisting/denylisting

#### 1.2 Code Examples & Sample Configurations

**Environment Variables Template**
```env
# OAuth2 Provider Configuration
OAUTH2_PROVIDER=okta|azure|google|auth0|keycloak
OAUTH2_CLIENT_ID=your-client-id
OAUTH2_CLIENT_SECRET=your-client-secret
OAUTH2_AUTHORIZATION_URL=https://...
OAUTH2_TOKEN_URL=https://...
OAUTH2_USER_INFO_URL=https://...
OAUTH2_REDIRECT_URI=https://your-app.com/api/v1/auth/callback
OAUTH2_SCOPES=openid,profile,email

# Role Mapping (IdP group -> App role)
OAUTH2_ADMIN_GROUPS=admin,superusers
OAUTH2_USER_GROUPS=employees,contractors
```

**API Integration Examples**
- Python SDK usage examples
- cURL commands for automation
- JavaScript/TypeScript client examples
- Postman collection export

#### 1.3 Troubleshooting Guide
- Common integration issues
- Token validation errors
- Role mapping problems
- Debugging checklist
- Support escalation paths

### Deliverables
- [ ] 7 comprehensive documentation files
- [ ] Architecture diagrams (using Mermaid)
- [ ] Sample configuration files
- [ ] API integration examples in 3+ languages
- [ ] Troubleshooting guide with FAQs
- [ ] Update main documentation index with enterprise section

---

## 2. Admin-Level Label/Tag Management System

### Objective
Create a centralized, admin-controlled label/tag management system that allows:
- Standardized label creation and maintenance
- Bulk label operations across resources
- Label categories/hierarchies
- Advanced filtering by label combinations
- Label templates for resource types

### Current State Analysis
- ✅ Resources have `tags` field (JSON array of strings)
- ✅ Search API supports tag filtering
- ✅ CSV import supports tags
- ⚠️  Missing: Centralized tag management
- ⚠️  Missing: Tag validation/standardization
- ⚠️  Missing: Admin UI for tag operations
- ⚠️  Missing: Tag categories and metadata

### Implementation Plan

#### 2.1 Backend Implementation

**a) Database Schema Updates**

Create new `Tag` model in `/apps/backend/app/models.py`:
```python
class Tag(Base):
    __tablename__ = "tags"

    id: int (PK)
    name: str (unique, indexed)
    display_name: str
    description: str | None
    color: str  # Hex color for UI
    category: str | None  # e.g., "hardware", "location", "capability"
    icon: str | None  # Icon identifier
    metadata: JSON  # Flexible metadata
    is_system: bool  # System tags (non-deletable)
    created_at: datetime
    updated_at: datetime
    created_by_id: int (FK -> User)

class ResourceTag(Base):
    __tablename__ = "resource_tags"

    resource_id: int (FK -> Resource)
    tag_id: int (FK -> Tag)
    assigned_at: datetime
    assigned_by_id: int (FK -> User)
```

**Migration Strategy:**
- Create migration to convert existing JSON tags to Tag table
- Maintain backward compatibility during transition
- Add indexes for performance (tag.name, resource_tag.resource_id, resource_tag.tag_id)

**b) API Endpoints**

Create `/apps/backend/app/routers/tags.py`:

```
Admin Tag Management:
  POST   /api/v1/admin/tags              - Create new tag
  GET    /api/v1/admin/tags              - List all tags (paginated)
  GET    /api/v1/admin/tags/{id}         - Get tag details
  PUT    /api/v1/admin/tags/{id}         - Update tag
  DELETE /api/v1/admin/tags/{id}         - Delete tag (if not in use)
  GET    /api/v1/admin/tags/categories   - List tag categories
  POST   /api/v1/admin/tags/bulk         - Bulk tag operations

Resource Tagging:
  POST   /api/v1/resources/{id}/tags     - Add tags to resource
  DELETE /api/v1/resources/{id}/tags     - Remove tags from resource
  PUT    /api/v1/resources/{id}/tags     - Replace all tags
  GET    /api/v1/resources/{id}/tags     - Get resource tags

Bulk Operations:
  POST   /api/v1/admin/tags/bulk/assign  - Assign tag to multiple resources
  POST   /api/v1/admin/tags/bulk/remove  - Remove tag from multiple resources
  POST   /api/v1/admin/tags/bulk/replace - Replace tag across all resources

Search & Discovery:
  GET    /api/v1/tags                    - Public tag list (for search)
  GET    /api/v1/tags/suggest            - Tag autocomplete
  GET    /api/v1/resources/by-tags       - Advanced tag-based search
```

**c) Tag Services**

Create `/apps/backend/app/services/tag_service.py`:
- TagService class for tag CRUD operations
- Tag validation (prevent duplicates, reserved names)
- Tag usage statistics
- Orphaned tag cleanup
- Tag merge functionality
- Tag suggestion/autocomplete logic

**d) Permissions & Authorization**

Update RBAC policies in `/apps/backend/app/rbac.py`:
```python
# Admin permissions
admin_permissions = [
    ("tags", "create"),
    ("tags", "read"),
    ("tags", "update"),
    ("tags", "delete"),
    ("tags", "bulk_assign"),
]

# User permissions (read-only for tags)
user_permissions = [
    ("tags", "read"),
]
```

#### 2.2 Frontend Implementation

**a) Admin Tag Management Page**

Create `/apps/frontend/src/app/admin/tags/page.tsx`:

Features:
- Tag list view with search/filter
- Tag creation dialog
- Tag editing interface
- Tag deletion with usage warnings
- Tag category management
- Color picker for tag colors
- Icon selector
- Bulk operations UI

**b) Resource Tagging Component**

Create `/apps/frontend/src/components/ResourceTagEditor.tsx`:

Features:
- Tag selector with autocomplete
- Visual tag display (colored badges)
- Add/remove tags interface
- Tag suggestions based on resource type
- Tag validation feedback

**c) Tag-Based Resource Search**

Enhance `/apps/frontend/src/components/ResourceSearch.tsx`:

Features:
- Tag filter chips
- Multi-tag selection (AND/OR logic)
- Tag category filters
- "Find resources with tags X AND Y" functionality
- Save tag filter presets

**d) Tag Usage Analytics**

Create `/apps/frontend/src/components/admin/TagAnalytics.tsx`:

Features:
- Most used tags
- Tag usage trends
- Untagged resources report
- Tag coverage percentage
- Tag standardization suggestions

#### 2.3 Tag Categories & Templates

**Predefined Tag Categories:**
```yaml
categories:
  - hardware:
      description: "Physical equipment types"
      examples: ["laptop", "monitor", "phone", "tablet"]

  - location:
      description: "Physical location or building"
      examples: ["building-a", "lab-1", "datacenter"]

  - capability:
      description: "Resource capabilities or features"
      examples: ["4k-display", "usb-c", "wireless", "vr-capable"]

  - status:
      description: "Operational status indicators"
      examples: ["production", "testing", "maintenance", "deprecated"]

  - access-level:
      description: "Access restrictions"
      examples: ["public", "internal", "restricted", "confidential"]

  - resource-type:
      description: "Type classification"
      examples: ["test-equipment", "conference-room", "vehicle", "tool"]
```

**Tag Templates for Common Resource Types:**
```yaml
test-equipment-template:
  required_tags: ["resource-type:test-equipment"]
  suggested_tags: ["location", "capability", "access-level"]

conference-room-template:
  required_tags: ["resource-type:conference-room"]
  suggested_tags: ["location", "capacity:*", "video-enabled", "recording-enabled"]
```

#### 2.4 Migration & Backward Compatibility

**Migration Script:**
- Analyze existing JSON tags across all resources
- Create Tag records for unique tags
- Create ResourceTag associations
- Preserve tag assignment history
- Generate migration report

**Backward Compatibility:**
- Keep `Resource.tags` JSON field during transition
- Sync both systems for 1-2 releases
- Provide deprecation warnings
- Remove JSON field in future major version

### Deliverables
- [ ] Database migrations for Tag and ResourceTag models
- [ ] Tag router with 15+ endpoints
- [ ] TagService with full CRUD and bulk operations
- [ ] Admin tag management UI (page + components)
- [ ] Resource tag editor component
- [ ] Enhanced tag-based search
- [ ] Tag analytics dashboard
- [ ] Migration script for existing tags
- [ ] API documentation for tag endpoints
- [ ] User guide for tag management

---

## 3. Automated Testing Integration & Squatter Detection

### Objective
Enable automated test frameworks to reserve test equipment programmatically and implement detection/eviction of idle or abandoned reservations ("squatters").

### Current State Analysis
- ✅ Reservation API exists
- ✅ API authentication with tokens
- ✅ Audit logging tracks reservation activity
- ⚠️  Missing: Service account support for automation
- ⚠️  Missing: Squatter detection logic
- ⚠️  Missing: Automated eviction system
- ⚠️  Missing: Integration guides for CI/CD

### Implementation Plan

#### 3.1 Service Accounts for Automation

**a) Database Model**

Create `ServiceAccount` model in `/apps/backend/app/models.py`:
```python
class ServiceAccount(Base):
    __tablename__ = "service_accounts"

    id: int (PK)
    name: str  # e.g., "Jenkins Test Runner"
    description: str
    api_key_hash: str  # Hashed API key
    api_key_prefix: str  # First 8 chars for identification
    role_id: int (FK -> Role)
    created_by_id: int (FK -> User)
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None
    is_active: bool
    allowed_ips: JSON  # IP allowlist
    allowed_resources: JSON  # Resource restrictions
    rate_limit_tier: str  # Custom rate limits
    metadata: JSON  # Custom metadata (e.g., CI job info)
```

**b) API Key Generation**

Create `/apps/backend/app/routers/service_accounts.py`:
```
POST   /api/v1/admin/service-accounts         - Create service account
GET    /api/v1/admin/service-accounts         - List service accounts
GET    /api/v1/admin/service-accounts/{id}    - Get details
PUT    /api/v1/admin/service-accounts/{id}    - Update
DELETE /api/v1/admin/service-accounts/{id}    - Revoke
POST   /api/v1/admin/service-accounts/{id}/rotate-key - Rotate API key
GET    /api/v1/admin/service-accounts/{id}/usage      - Usage statistics
```

**c) Authentication Enhancement**

Update `/apps/backend/app/auth.py`:
- Add API key authentication scheme
- Support Bearer token with `sa_` prefix for service accounts
- Validate API key and load service account
- Apply service account permissions and restrictions

#### 3.2 Squatter Detection System

**a) Squatter Detection Service**

Create `/apps/backend/app/services/squatter_detection.py`:

```python
class SquatterDetectionService:
    """Detect and manage idle/abandoned reservations"""

    async def detect_squatters(self, criteria: SquatterCriteria):
        """
        Detect squatters based on:
        - Reservation held longer than max duration
        - No activity/check-in during reservation
        - Resource marked as unused but reserved
        - Reservation past end time but not released
        """

    async def calculate_idle_time(self, reservation_id: int):
        """Calculate how long reservation has been idle"""

    async def send_warning(self, reservation_id: int):
        """Send warning notification to reservation owner"""

    async def auto_release(self, reservation_id: int, reason: str):
        """Automatically release/cancel reservation"""

    async def get_squatter_report(self):
        """Generate squatter activity report"""
```

**Detection Criteria:**
```python
class SquatterCriteria:
    max_idle_time: int = 30  # minutes
    max_reservation_duration: int = 24  # hours
    check_in_required: bool = True
    check_in_interval: int = 60  # minutes
    grace_period: int = 15  # minutes before eviction
    exclude_resources: list[int] = []
    exclude_users: list[int] = []  # VIP users exempt
```

**b) Activity Tracking**

Create `ReservationActivity` model:
```python
class ReservationActivity(Base):
    __tablename__ = "reservation_activities"

    id: int (PK)
    reservation_id: int (FK -> Reservation)
    activity_type: str  # "check_in", "usage_detected", "manual_ping"
    timestamp: datetime
    source: str  # "api", "webhook", "auto"
    metadata: JSON  # e.g., IP address, user agent
```

**c) Check-In API**

Add endpoints to `/apps/backend/app/routers/reservations.py`:
```
POST   /api/v1/reservations/{id}/checkin      - User check-in (I'm still using this)
POST   /api/v1/reservations/{id}/heartbeat    - Automated heartbeat
GET    /api/v1/reservations/{id}/activity     - Get activity log
```

**d) Squatter Detection Scheduler**

Create background job in `/apps/backend/app/scheduler.py`:
```python
@scheduler.scheduled_job('interval', minutes=5)
async def detect_and_evict_squatters():
    """Run squatter detection every 5 minutes"""
    service = SquatterDetectionService()

    # Find potential squatters
    squatters = await service.detect_squatters(criteria)

    for squatter in squatters:
        # Send warning if first detection
        if not squatter.warning_sent:
            await service.send_warning(squatter.reservation_id)

        # Evict if grace period expired
        elif squatter.grace_period_expired:
            await service.auto_release(
                squatter.reservation_id,
                reason="Automatic eviction due to inactivity"
            )
```

#### 3.3 Automated Testing Integration

**a) Documentation**

Create `/docs/integrations/automated-testing.md`:

Content:
- Overview of automation capabilities
- Service account setup
- API authentication for CI/CD
- Reservation workflow for test jobs
- Check-in/heartbeat implementation
- Error handling and retries
- Best practices

**b) SDK/Client Libraries**

Create Python SDK in `/sdk/python/`:
```python
from resource_reserver import Client, ServiceAccountAuth

# Initialize client
client = Client(
    base_url="https://resource-reserver.example.com",
    auth=ServiceAccountAuth(api_key="sa_xxxxx")
)

# Reserve test equipment
reservation = client.reservations.create(
    resource_id=123,
    start_time="2024-01-15T10:00:00Z",
    end_time="2024-01-15T12:00:00Z",
    purpose="Automated integration tests - Build #456",
    metadata={
        "ci_job": "integration-tests",
        "build_number": 456,
        "git_commit": "abc123"
    }
)

# Send heartbeat during test execution
with client.reservations.heartbeat(reservation.id, interval=60):
    # Run your tests
    run_tests()

# Automatically released after context manager exits
```

**c) CI/CD Integration Examples**

Create examples for common CI/CD platforms:

**GitHub Actions** (`.github/workflows/reserve-equipment.yml`):
```yaml
name: Integration Tests with Equipment Reservation

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Reserve Test Equipment
        id: reserve
        uses: resource-reserver/reserve-action@v1
        with:
          api_url: ${{ secrets.RESOURCE_RESERVER_URL }}
          api_key: ${{ secrets.RESOURCE_RESERVER_API_KEY }}
          resource_tags: "test-equipment,5g-capable"
          duration: 30m

      - name: Run Tests
        run: |
          pytest tests/ --equipment-id=${{ steps.reserve.outputs.resource_id }}

      - name: Release Equipment
        if: always()
        uses: resource-reserver/release-action@v1
        with:
          reservation_id: ${{ steps.reserve.outputs.reservation_id }}
```

**Jenkins** (Jenkinsfile):
```groovy
pipeline {
    agent any

    environment {
        RR_API_KEY = credentials('resource-reserver-api-key')
    }

    stages {
        stage('Reserve Equipment') {
            steps {
                script {
                    def reservation = sh(
                        script: '''
                            curl -X POST https://rr.example.com/api/v1/reservations \
                              -H "Authorization: Bearer ${RR_API_KEY}" \
                              -H "Content-Type: application/json" \
                              -d '{"resource_id": 123, "duration": "30m"}'
                        ''',
                        returnStdout: true
                    )
                    env.RESERVATION_ID = parseJson(reservation).id
                }
            }
        }

        stage('Run Tests') {
            steps {
                sh 'pytest tests/'
            }
        }
    }

    post {
        always {
            sh 'curl -X POST https://rr.example.com/api/v1/reservations/${RESERVATION_ID}/cancel'
        }
    }
}
```

**GitLab CI** (`.gitlab-ci.yml`):
```yaml
test:
  stage: test
  script:
    - pip install resource-reserver-sdk
    - python scripts/reserve_and_test.py
  after_script:
    - python scripts/release_equipment.py
```

**d) Webhook Integration for Test Results**

Allow test frameworks to send results back:

```
POST /api/v1/reservations/{id}/test-results
{
  "status": "passed|failed|error",
  "test_count": 42,
  "failure_count": 0,
  "duration": 1234,
  "report_url": "https://ci.example.com/build/456",
  "metadata": {}
}
```

#### 3.4 Squatter Prevention Features

**a) Auto-Extension Prevention**

Add configuration to limit auto-extensions:
```python
class ResourceConfig:
    max_consecutive_reservations: int = 3  # Max back-to-back reservations
    min_gap_between_reservations: int = 15  # Minutes required between reservations
    max_total_hours_per_day: int = 8  # Max hours per user per day
```

**b) Fairness Policies**

Create `/apps/backend/app/services/fairness.py`:
```python
class FairnessService:
    async def check_reservation_fairness(self, user_id: int, resource_id: int):
        """
        Check if reservation request is fair:
        - User hasn't exceeded daily/weekly quotas
        - Not monopolizing high-demand resources
        - Respecting queue/waitlist
        """

    async def calculate_priority_score(self, user_id: int):
        """Calculate user's priority based on usage history"""
```

**c) Admin Dashboard for Squatter Management**

Create `/apps/frontend/src/app/admin/squatters/page.tsx`:

Features:
- Live list of potential squatters
- Idle time indicators
- Manual eviction button
- Squatter history/trends
- Exemption management (VIP users/resources)
- Squatter detection configuration

#### 3.5 Monitoring & Alerting

**a) Squatter Metrics**

Add to `/apps/backend/app/routers/analytics.py`:
```
GET /api/v1/analytics/squatters/summary
{
  "total_detections_today": 12,
  "auto_evictions_today": 5,
  "warnings_sent_today": 7,
  "avg_idle_time": 45,
  "top_squatters": [...]
}
```

**b) Alerting Configuration**

Create admin settings for squatter alerts:
- Email admins on detection
- Slack/Teams webhook notifications
- Daily squatter report
- Threshold-based alerts (>X squatters)

### Deliverables
- [ ] ServiceAccount model and API key system
- [ ] Service account management API (7 endpoints)
- [ ] Squatter detection service with configurable criteria
- [ ] ReservationActivity tracking model
- [ ] Check-in/heartbeat API endpoints
- [ ] Squatter detection scheduler (background job)
- [ ] Python SDK for automation
- [ ] CI/CD integration examples (GitHub Actions, Jenkins, GitLab)
- [ ] Automation documentation guide
- [ ] Admin squatter management UI
- [ ] Squatter analytics and reporting
- [ ] Webhook integration for test results

---

## Implementation Timeline & Dependencies

### Phase 1: Documentation & Planning (Week 1)
- Create enterprise OAuth2 documentation
- Design tag management schema
- Design service account system
- Review and finalize specifications

### Phase 2: Backend Implementation (Weeks 2-3)
- Tag management system (database + API)
- Service accounts (database + API)
- Squatter detection service
- Migration scripts

### Phase 3: Frontend Implementation (Week 4)
- Admin tag management UI
- Resource tag editor
- Service account management UI
- Squatter dashboard

### Phase 4: Integrations & SDKs (Week 5)
- Python SDK for automation
- CI/CD integration examples
- Webhook handlers
- Testing and validation

### Phase 5: Documentation & Testing (Week 6)
- Complete all documentation
- Integration testing
- Performance testing
- Security review

---

## Testing Strategy

### Unit Tests
- Tag CRUD operations
- Service account authentication
- Squatter detection logic
- API key generation and validation

### Integration Tests
- OAuth2 provider integration
- Tag migration from JSON to relational
- CI/CD automation workflows
- Squatter detection + eviction flow

### Performance Tests
- Tag search performance with 10k+ tags
- Squatter detection at scale (1000+ concurrent reservations)
- API key authentication overhead

### Security Tests
- API key security and rotation
- OAuth2 token validation
- RBAC enforcement for tag operations
- SQL injection prevention in tag queries

---

## Rollback & Risk Mitigation

### Tag System Migration
- **Risk:** Data loss during JSON to relational migration
- **Mitigation:** Backup database, run migration in transaction, keep dual-write for 2 releases
- **Rollback:** Revert migration, continue using JSON tags

### Squatter Detection
- **Risk:** False positives evicting legitimate users
- **Mitigation:** Conservative thresholds, warning period, exemption list, audit logging
- **Rollback:** Disable scheduler, manual review only

### Service Accounts
- **Risk:** API key compromise
- **Mitigation:** Key rotation, IP allowlisting, rate limiting, audit logging
- **Rollback:** Revoke compromised keys, regenerate

---

## Success Metrics

### OAuth2 Documentation
- ✅ Integration time reduced from 2 days to 4 hours
- ✅ 90%+ of users successfully configure OAuth2 without support
- ✅ Zero security incidents related to misconfiguration

### Tag Management
- ✅ 100% of resources tagged within 30 days
- ✅ Tag search usage increases by 200%
- ✅ Resource discovery time reduced by 50%

### Automated Testing
- ✅ 10+ CI/CD pipelines integrated within 3 months
- ✅ Test equipment utilization increases by 30%
- ✅ Squatter evictions reduce idle time by 40%

---

## Next Steps

1. **Review this plan** - Confirm priorities and scope
2. **Set up tracking** - Create GitHub issues/project board
3. **Begin Phase 1** - Start with documentation and schema design
4. **Iterative development** - Implement feature by feature with continuous feedback

Would you like me to proceed with implementation? If so, please indicate:
- Which enhancement to start with (OAuth2 docs, tag management, or automation)?
- Any modifications to the plan?
- Any specific requirements or constraints?
