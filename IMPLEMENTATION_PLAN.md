# Resource-Reserver: 2-3 Day Implementation Plan

> **Goal**: Ship high-impact improvements in 2-3 days with AI assistance **Constraint**: Each PR touches 10-15 files maximum **Total PRs**: 8 PRs across 3 days

______________________________________________________________________

## Day 1: Foundation & Security (3 PRs)

### PR #1: API Versioning & Rate Limiting

**Branch**: `feat/api-v1-rate-limiting` **Files**: ~8 files **Time**: 2-3 hours

#### Tasks

- [ ] Create `/api/v1/` prefix structure
- [ ] Add `slowapi` for rate limiting
- [ ] Configure tiered rate limits (anonymous/authenticated/admin)
- [ ] Add rate limit headers to responses
- [ ] Update OpenAPI docs

#### Files to Modify

```
app/main.py                    # Add versioned router, rate limiter
app/routers/__init__.py        # Export v1 router
app/dependencies.py            # Add rate limit dependency (create if needed)
app/config.py                  # Add rate limit settings (create if needed)
pyproject.toml                 # Add slowapi dependency
frontend-next/src/lib/api.ts   # Update API base path
tests/conftest.py              # Update test client for /api/v1
docs/api-reference.md          # Document new versioning
```

#### Implementation Notes

```python
# app/main.py additions
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

v1_router = APIRouter(prefix="/api/v1")
# Mount all existing routers under v1_router
```

______________________________________________________________________

### PR #2: Refresh Tokens & Session Improvements

**Branch**: `feat/refresh-tokens` **Files**: ~10 files **Time**: 3-4 hours

#### Tasks

- [ ] Create `RefreshToken` model
- [ ] Add `/api/v1/token/refresh` endpoint
- [ ] Update login to return both tokens
- [ ] Add token family tracking (for rotation)
- [ ] Update frontend auth context
- [ ] Add automatic token refresh in axios interceptor

#### Files to Modify

```
app/models.py                           # Add RefreshToken model
app/auth.py                             # Add refresh token logic
app/routers/auth.py                     # Add refresh endpoint (create if separate)
app/schemas.py                          # Add TokenRefresh schemas
frontend-next/src/lib/api.ts            # Add axios interceptor for refresh
frontend-next/src/contexts/AuthContext.tsx  # Handle refresh tokens (create/update)
frontend-next/src/app/login/page.tsx    # Update login handling
tests/test_api/test_auth.py             # Add refresh token tests
alembic/versions/xxx_add_refresh_tokens.py  # Migration (if using alembic)
```

#### Token Structure

```python
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False)  # Hashed token
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    revoked = Column(Boolean, default=False)
    family_id = Column(String, nullable=False)  # For token rotation
```

______________________________________________________________________

### PR #3: Account Security (Lockout & Password Policy)

**Branch**: `feat/account-security` **Files**: ~9 files **Time**: 2-3 hours

#### Tasks

- [ ] Create `LoginAttempt` model for tracking
- [ ] Implement account lockout after 5 failed attempts
- [ ] Add password strength validation
- [ ] Add password policy configuration
- [ ] Update registration/password change flows
- [ ] Add user-friendly error messages

#### Files to Modify

```
app/models.py                          # Add LoginAttempt model
app/auth.py                            # Add lockout check, password validation
app/services.py                        # Add login attempt tracking
app/schemas.py                         # Add password validation schema
app/utils/password.py                  # Password policy utilities (create)
frontend-next/src/components/PasswordStrengthMeter.tsx  # Visual feedback (create)
frontend-next/src/app/login/page.tsx   # Show lockout message
tests/test_api/test_auth.py            # Add lockout tests
```

#### Password Policy

```python
# app/utils/password.py
import re
from typing import List, Tuple


class PasswordPolicy:
    MIN_LENGTH = 10
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True

    @classmethod
    def validate(cls, password: str, username: str = "") -> Tuple[bool, List[str]]:
        errors = []

        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Password must be at least {cls.MIN_LENGTH} characters")
        if cls.REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
            errors.append("Password must contain an uppercase letter")
        if cls.REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
            errors.append("Password must contain a lowercase letter")
        if cls.REQUIRE_DIGIT and not re.search(r"\d", password):
            errors.append("Password must contain a number")
        if cls.REQUIRE_SPECIAL and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            errors.append("Password must contain a special character")
        if username and username.lower() in password.lower():
            errors.append("Password cannot contain your username")

        return len(errors) == 0, errors
```

______________________________________________________________________

## Day 2: User Experience (3 PRs)

### PR #4: Pagination & Enhanced Filtering

**Branch**: `feat/pagination-filtering` **Files**: ~12 files **Time**: 3-4 hours

#### Tasks

- [ ] Add cursor-based pagination to list endpoints
- [ ] Enhance resource search with more filters
- [ ] Add sorting options
- [ ] Update frontend to handle pagination
- [ ] Add "Load More" / infinite scroll option

#### Files to Modify

```
app/schemas.py                              # Add PaginatedResponse schema
app/services.py                             # Add pagination logic to services
app/routers/resources.py                    # Update list/search endpoints
app/routers/reservations.py                 # Update my reservations endpoint
frontend-next/src/lib/api.ts                # Add pagination params
frontend-next/src/hooks/usePagination.ts    # Pagination hook (create)
frontend-next/src/components/ResourceList.tsx      # Add load more
frontend-next/src/components/ReservationList.tsx   # Add load more
frontend-next/src/components/Pagination.tsx        # Pagination component (create)
tests/test_api/test_resources.py            # Add pagination tests
tests/test_api/test_reservations.py         # Add pagination tests
```

#### Pagination Schema

```python
# app/schemas.py
from typing import Generic, TypeVar, Optional, List

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    next_cursor: Optional[str] = None
    prev_cursor: Optional[str] = None
    has_more: bool
    total_count: Optional[int] = None  # Optional for performance


class PaginationParams(BaseModel):
    cursor: Optional[str] = None
    limit: int = Field(default=20, le=100, ge=1)
    sort_by: Optional[str] = "created_at"
    sort_order: Optional[str] = "desc"
```

______________________________________________________________________

### PR #5: Notification Foundation (In-App)

**Branch**: `feat/notifications` **Files**: ~14 files **Time**: 4-5 hours

#### Tasks

- [ ] Create `Notification` model
- [ ] Add notification service
- [ ] Create notification endpoints (list, mark read, mark all read)
- [ ] Build notification center UI component
- [ ] Add notification triggers for key events
- [ ] Add notification badge in header

#### Files to Modify

```
app/models.py                                      # Add Notification model
app/schemas.py                                     # Add notification schemas
app/services.py                                    # Add NotificationService
app/routers/notifications.py                       # Notification endpoints (create)
app/main.py                                        # Register notifications router
frontend-next/src/components/NotificationCenter.tsx    # UI component (create)
frontend-next/src/components/NotificationBadge.tsx     # Badge component (create)
frontend-next/src/components/NotificationItem.tsx      # Item component (create)
frontend-next/src/hooks/useNotifications.ts            # Notifications hook (create)
frontend-next/src/app/dashboard/page.tsx               # Add notification center
frontend-next/src/lib/api.ts                           # Add notification API calls
tests/test_api/test_notifications.py                   # Notification tests (create)
```

#### Notification Model

```python
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)  # reservation_confirmed, reminder, etc.
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    link = Column(String, nullable=True)  # Optional action link
    read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now())

    user = relationship("User", back_populates="notifications")
```

#### Notification Types

```python
class NotificationType(str, Enum):
    RESERVATION_CONFIRMED = "reservation_confirmed"
    RESERVATION_CANCELLED = "reservation_cancelled"
    RESERVATION_REMINDER = "reservation_reminder"
    RESOURCE_AVAILABLE = "resource_available"
    SYSTEM_ANNOUNCEMENT = "system_announcement"
```

______________________________________________________________________

### PR #6: Recurring Reservations (Basic)

**Branch**: `feat/recurring-reservations` **Files**: ~12 files **Time**: 4-5 hours

#### Tasks

- [ ] Create `RecurrenceRule` model
- [ ] Update `Reservation` model with recurrence fields
- [ ] Add recurrence logic to reservation service
- [ ] Create endpoints for recurring reservations
- [ ] Build recurrence UI in reservation form
- [ ] Handle conflicts for recurring instances

#### Files to Modify

```
app/models.py                                    # Add RecurrenceRule, update Reservation
app/schemas.py                                   # Add recurrence schemas
app/services.py                                  # Add recurring reservation logic
app/routers/reservations.py                      # Add/update endpoints
app/utils/recurrence.py                          # Recurrence calculation utils (create)
frontend-next/src/components/RecurrenceSelector.tsx  # UI component (create)
frontend-next/src/components/ReservationForm.tsx     # Update with recurrence
frontend-next/src/components/RecurringBadge.tsx      # Badge indicator (create)
frontend-next/src/lib/api.ts                         # Add recurrence API calls
tests/test_api/test_reservations.py                  # Add recurrence tests
tests/test_services/test_recurrence.py               # Unit tests (create)
```

#### Recurrence Model

```python
class RecurrenceRule(Base):
    __tablename__ = "recurrence_rules"

    id = Column(Integer, primary_key=True)
    frequency = Column(String, nullable=False)  # daily, weekly, monthly
    interval = Column(Integer, default=1)  # Every N periods
    days_of_week = Column(JSON, nullable=True)  # [0,1,2,3,4] for weekdays
    end_type = Column(String, nullable=False)  # never, on_date, after_count
    end_date = Column(DateTime(timezone=True), nullable=True)
    occurrence_count = Column(Integer, nullable=True)

    reservations = relationship("Reservation", back_populates="recurrence_rule")


# Update Reservation model
class Reservation(Base):
    # ... existing fields
    recurrence_rule_id = Column(
        Integer, ForeignKey("recurrence_rules.id"), nullable=True
    )
    parent_reservation_id = Column(
        Integer, ForeignKey("reservations.id"), nullable=True
    )
    is_recurring_instance = Column(Boolean, default=False)
```

______________________________________________________________________

## Day 3: Polish & Real-Time (2 PRs)

### PR #7: WebSocket Real-Time Updates

**Branch**: `feat/websocket-realtime` **Files**: ~10 files **Time**: 3-4 hours

#### Tasks

- [ ] Add WebSocket endpoint in FastAPI
- [ ] Create connection manager for users
- [ ] Broadcast resource status changes
- [ ] Broadcast reservation updates
- [ ] Build React WebSocket context
- [ ] Update dashboard with live updates

#### Files to Modify

```
app/websocket.py                                # WebSocket manager (create)
app/main.py                                     # Add WebSocket route
app/routers/resources.py                        # Emit events on changes
app/routers/reservations.py                     # Emit events on changes
frontend-next/src/contexts/WebSocketContext.tsx # WS context (create)
frontend-next/src/hooks/useWebSocket.ts         # WS hook (create)
frontend-next/src/app/layout.tsx                # Add WS provider
frontend-next/src/app/dashboard/page.tsx        # Subscribe to updates
frontend-next/src/components/LiveIndicator.tsx  # Live status indicator (create)
tests/test_websocket.py                         # WebSocket tests (create)
```

#### WebSocket Manager

```python
# app/websocket.py
from fastapi import WebSocket
from typing import Dict, Set
import json


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)

    async def broadcast_to_user(self, user_id: int, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(message)

    async def broadcast_all(self, message: dict):
        for connections in self.active_connections.values():
            for connection in connections:
                await connection.send_json(message)


manager = ConnectionManager()
```

______________________________________________________________________

### PR #8: Waitlist & Resource Availability Alerts

**Branch**: `feat/waitlist` **Files**: ~13 files **Time**: 4-5 hours

#### Tasks

- [ ] Create `Waitlist` model
- [ ] Add waitlist service with auto-offer logic
- [ ] Create waitlist endpoints
- [ ] Build waitlist UI components
- [ ] Integrate with notification system
- [ ] Add "Join Waitlist" button on unavailable resources

#### Files to Modify

```
app/models.py                                    # Add Waitlist model
app/schemas.py                                   # Add waitlist schemas
app/services.py                                  # Add WaitlistService
app/routers/waitlist.py                          # Waitlist endpoints (create)
app/main.py                                      # Register waitlist router
frontend-next/src/components/WaitlistButton.tsx      # Join waitlist (create)
frontend-next/src/components/WaitlistStatus.tsx      # Status component (create)
frontend-next/src/components/WaitlistManager.tsx     # Manage position (create)
frontend-next/src/app/dashboard/page.tsx             # Add waitlist section
frontend-next/src/lib/api.ts                         # Add waitlist API calls
tests/test_api/test_waitlist.py                      # Waitlist tests (create)
docs/api-reference.md                                # Document waitlist API
```

#### Waitlist Model

```python
class Waitlist(Base):
    __tablename__ = "waitlist"

    id = Column(Integer, primary_key=True)
    resource_id = Column(Integer, ForeignKey("resources.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    desired_start = Column(DateTime(timezone=True), nullable=False)
    desired_end = Column(DateTime(timezone=True), nullable=False)
    flexible_time = Column(Boolean, default=False)  # Can adjust time if needed
    status = Column(
        String, default="waiting"
    )  # waiting, offered, expired, fulfilled, cancelled
    position = Column(Integer, nullable=False)  # Queue position
    created_at = Column(DateTime(timezone=True), default=func.now())
    offered_at = Column(DateTime(timezone=True), nullable=True)
    offer_expires_at = Column(DateTime(timezone=True), nullable=True)

    resource = relationship("Resource", back_populates="waitlist_entries")
    user = relationship("User", back_populates="waitlist_entries")
```

______________________________________________________________________

## Quick Reference: PR Checklist

For each PR, ensure:

- [ ] Branch created from latest `main`
- [ ] All new files have proper imports
- [ ] Tests written and passing
- [ ] Linting passes (`ruff check .`)
- [ ] Type hints added
- [ ] API docs updated if endpoints changed
- [ ] Frontend builds without errors
- [ ] Migrations created if models changed
- [ ] PR description includes:
  - Summary of changes
  - Test plan
  - Screenshots (for UI changes)

______________________________________________________________________

## Dependencies to Add

```toml
# pyproject.toml additions across PRs

# PR #1: Rate Limiting
slowapi = "^0.1.9"

# PR #7: WebSockets (already in fastapi, but may need)
websockets = "^12.0"

# Optional: Better async task handling
aiofiles = "^23.0"
```

```json
// frontend-next/package.json additions

// PR #5: Notifications
// (No new deps needed - use existing Radix UI)

// PR #7: WebSockets
// (Native WebSocket API, no deps needed)
```

______________________________________________________________________

## Daily Schedule

### Day 1 (Foundation)

| Time           | Task                           | PR  |
| -------------- | ------------------------------ | --- |
| Morning (3h)   | API Versioning + Rate Limiting | #1  |
| Afternoon (4h) | Refresh Tokens                 | #2  |
| Evening (3h)   | Account Security               | #3  |

### Day 2 (UX)

| Time           | Task                   | PR  |
| -------------- | ---------------------- | --- |
| Morning (4h)   | Pagination & Filtering | #4  |
| Afternoon (5h) | Notification System    | #5  |
| Evening (4h)   | Recurring Reservations | #6  |

### Day 3 (Polish)

| Time           | Task                | PR  |
| -------------- | ------------------- | --- |
| Morning (4h)   | WebSocket Real-Time | #7  |
| Afternoon (5h) | Waitlist System     | #8  |
| Evening        | Testing & Bug Fixes | -   |

______________________________________________________________________

## Post-Implementation Checklist

After all PRs are merged:

- [ ] Run full test suite
- [ ] Update CHANGELOG.md
- [ ] Update version in pyproject.toml
- [ ] Update API documentation
- [ ] Test all features end-to-end
- [ ] Create release tag
- [ ] Deploy to staging environment
- [ ] Smoke test production deployment

______________________________________________________________________

## Commands Reference

```bash
# Start development
mise run dev

# Run backend only
mise run backend-dev

# Run frontend only
mise run frontend-dev

# Run tests
mise run test

# Lint and format
mise run lint
mise run format

# Build for production
mise run build
```

______________________________________________________________________

## Notes for AI Assistance

When working with AI on each PR:

1. **Start each PR session with**: "I'm working on PR #X: [name]. Here's the plan: [paste relevant section]"

1. **For each file**: Ask AI to generate the complete implementation based on the specification

1. **Testing**: Ask AI to generate comprehensive tests for each new feature

1. **Review**: Before committing, ask AI to review the changes for potential issues

1. **Conflicts**: If you encounter issues, describe the error and ask for fixes

______________________________________________________________________

______________________________________________________________________

## CLI Backlog (Post-Sprint or Parallel)

Track CLI features that need implementation to maintain parity with web interface.

### CLI PR #A: Auth & API Updates

**Branch**: `feat/cli-auth-updates` **Files**: ~5 files **Depends on**: PR #1, #2, #3

#### Tasks

- [ ] Update base URL to `/api/v1/`
- [ ] Implement refresh token storage in config file
- [ ] Add automatic token refresh before expiry
- [ ] Display password policy errors on registration
- [ ] Show account lockout message with remaining time

#### Files to Modify

```
cli/config.py              # Update API base path, add refresh token storage
cli/auth.py                # Add refresh token logic
cli/commands/auth.py       # Update login/register with better error handling
cli/utils.py               # Add token refresh helper
tests/test_cli/test_auth_cli.py  # Update tests
```

______________________________________________________________________

### CLI PR #B: Pagination Support

**Branch**: `feat/cli-pagination` **Files**: ~4 files **Depends on**: PR #4

#### Tasks

- [ ] Add `--limit` flag to list commands (default 20)
- [ ] Add `--cursor` flag for pagination
- [ ] Add `--all` flag to fetch everything (with warning)
- [ ] Display "Showing X of Y" and next cursor hint
- [ ] Add `--sort` and `--order` flags

#### Files to Modify

```
cli/commands/resources.py      # Add pagination flags
cli/commands/reservations.py   # Add pagination flags
cli/utils.py                   # Add pagination helper
tests/test_cli/test_resources_cli.py  # Update tests
```

#### Example Usage

```bash
# List first 20 resources
resource-reserver-cli resources list

# List next page
resource-reserver-cli resources list --cursor "eyJpZCI6IDIwfQ=="

# List with custom limit
resource-reserver-cli resources list --limit 50

# Fetch all (with confirmation)
resource-reserver-cli resources list --all
```

______________________________________________________________________

### CLI PR #C: Recurring Reservations

**Branch**: `feat/cli-recurring` **Files**: ~3 files **Depends on**: PR #6

#### Tasks

- [ ] Add `--recurrence` flag to create command
- [ ] Add `--recurrence-end` flag (date or count)
- [ ] Add `--days` flag for weekly recurrence
- [ ] Display recurrence info in reservation details
- [ ] Add `reservations cancel-series` command

#### Files to Modify

```
cli/commands/reservations.py       # Add recurrence flags and commands
cli/schemas.py                     # Add recurrence schemas (if needed)
tests/test_cli/test_reservations_cli.py  # Update tests
```

#### Example Usage

```bash
# Create weekly recurring reservation (Mon, Wed, Fri)
resource-reserver-cli reservations create \
  --resource 1 \
  --start "2024-01-15 09:00" \
  --end "2024-01-15 10:00" \
  --recurrence weekly \
  --days 1,3,5 \
  --recurrence-end "2024-03-15"

# Create daily recurring (10 occurrences)
resource-reserver-cli reservations create \
  --resource 1 \
  --start "2024-01-15 09:00" \
  --end "2024-01-15 10:00" \
  --recurrence daily \
  --recurrence-count 10

# Cancel entire series
resource-reserver-cli reservations cancel-series 123
```

______________________________________________________________________

### CLI PR #D: Waitlist Commands

**Branch**: `feat/cli-waitlist` **Files**: ~4 files **Depends on**: PR #8

#### Tasks

- [ ] Add `waitlist join` command
- [ ] Add `waitlist leave` command
- [ ] Add `waitlist status` command
- [ ] Add `waitlist list` command (show user's waitlist entries)
- [ ] Add `waitlist accept` command (when offered)

#### Files to Modify

```
cli/commands/waitlist.py           # New waitlist commands (create)
cli/main.py                        # Register waitlist command group
cli/schemas.py                     # Add waitlist schemas (if needed)
tests/test_cli/test_waitlist_cli.py  # Waitlist tests (create)
```

#### Example Usage

```bash
# Join waitlist for a resource
resource-reserver-cli waitlist join \
  --resource 1 \
  --start "2024-01-15 09:00" \
  --end "2024-01-15 10:00" \
  --flexible  # Optional: accept nearby time slots

# Check waitlist status
resource-reserver-cli waitlist status

# View position in queue
resource-reserver-cli waitlist list

# Accept an offer (when notified)
resource-reserver-cli waitlist accept 456

# Leave waitlist
resource-reserver-cli waitlist leave 456
```

______________________________________________________________________

### CLI Feature Matrix

| Feature                  | Web PR | CLI PR | CLI Priority          |
| ------------------------ | ------ | ------ | --------------------- |
| API v1 base path         | #1     | #A     | High                  |
| Rate limit handling      | #1     | #A     | High (error handling) |
| Refresh tokens           | #2     | #A     | High                  |
| Password policy feedback | #3     | #A     | Medium                |
| Account lockout messages | #3     | #A     | Medium                |
| Pagination               | #4     | #B     | High                  |
| Sorting/filtering        | #4     | #B     | Medium                |
| Notifications            | #5     | N/A    | Not applicable        |
| Recurring reservations   | #6     | #C     | Medium                |
| WebSocket updates        | #7     | N/A    | Not applicable        |
| Waitlist                 | #8     | #D     | Medium                |

______________________________________________________________________

### CLI Implementation Schedule

**Option 1: Sequential (After Web Sprint)**

```
Day 4:
├── CLI PR #A: Auth & API Updates (2-3 hours)
└── CLI PR #B: Pagination Support (2 hours)

Day 5:
├── CLI PR #C: Recurring Reservations (2-3 hours)
└── CLI PR #D: Waitlist Commands (2-3 hours)
```

**Option 2: Parallel (During Web Sprint)**

```
Each day, after completing web PRs:
- Day 1 evening: CLI PR #A (pairs with PR #1, #2, #3)
- Day 2 evening: CLI PR #B (pairs with PR #4)
- Day 3 evening: CLI PR #C, #D (pairs with PR #6, #8)
```

______________________________________________________________________

*Generated: 2024-12-22* *Estimated Total Time: 24-30 hours over 3 days (Web) + 8-10 hours (CLI)* *Total Files Modified: ~90 across 8 PRs (Web) + ~16 across 4 PRs (CLI)*
