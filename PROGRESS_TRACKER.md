# Progress Tracker

## Day 1: Foundation & Security

### PR #1: API Versioning & Rate Limiting

- [x] Create branch `feat/api-v1-rate-limiting`
- [x] Add slowapi to pyproject.toml
- [x] Create app/config.py with settings
- [x] Update app/main.py with v1 router + rate limiter
- [x] Update frontend API base path
- [x] Update tests for /api/v1 prefix
- [x] Run tests: `pytest tests/test_api/`
- [x] Create PR (#12)
- [x] Merge PR

### PR #2: Refresh Tokens

- [x] Create branch `feat/refresh-tokens`
- [x] Add RefreshToken model to app/models.py
- [x] Add refresh logic to app/auth.py
- [x] Add /token/refresh endpoint
- [x] Update frontend AuthContext
- [x] Add axios interceptor for auto-refresh
- [x] Add tests
- [x] Run tests: `pytest tests/test_api/test_auth.py`
- [x] Create PR (#13)
- [ ] Merge PR

### PR #3: Account Security

- [x] Create branch `feat/account-security`
- [x] Add LoginAttempt model
- [x] Create app/utils/password.py
- [x] Add lockout check to login flow
- [x] Add PasswordStrengthMeter component
- [x] Update login page with lockout message
- [x] Add tests
- [x] Run tests: `pytest tests/test_api/test_auth.py -v` `pytest tests/test_services/test_user_service.py -v`
- [x] Create PR (#14)
- [ ] Merge PR

______________________________________________________________________

## Day 2: User Experience

### PR #4: Pagination & Filtering

- [x] Create branch `feat/pagination-filtering`
- [x] Add PaginatedResponse schema
- [x] Update ResourceService with pagination
- [x] Update ReservationService with pagination
- [x] Create usePagination hook
- [x] Update ResourceList component
- [x] Update ReservationList component
- [x] Add tests
- [x] Create PR (#15)
- [x] Merge PR

### PR #5: Notifications

- [x] Create branch `feat/notifications`
- [x] Add Notification model
- [x] Create NotificationService
- [x] Create app/routers/notifications.py
- [x] Register router in main.py
- [x] Create NotificationCenter component
- [x] Create NotificationBadge component
- [x] Create useNotifications hook
- [x] Update dashboard with notification center
- [x] Add tests
- [x] Create PR (#16)
- [x] Merge PR

### PR #6: Recurring Reservations

- [ ] Create branch `feat/recurring-reservations`
- [ ] Add RecurrenceRule model
- [ ] Update Reservation model
- [ ] Create app/utils/recurrence.py
- [ ] Update reservation service
- [ ] Create RecurrenceSelector component
- [ ] Update ReservationForm
- [ ] Add tests
- [ ] Create PR
- [ ] Merge PR

______________________________________________________________________

## Day 3: Polish & Real-Time

### PR #7: WebSocket Real-Time

- [x] Create branch `feat/websocket-realtime`
- [x] Create app/websocket.py
- [x] Add WebSocket route to main.py
- [x] Create WebSocketContext
- [x] Create useWebSocket hook
- [x] Add WS provider to layout
- [x] Update dashboard with live updates
- [x] Create LiveIndicator component
- [x] Add tests
- [ ] Create PR
- [ ] Merge PR

### PR #8: Waitlist

- [ ] Create branch `feat/waitlist`
- [ ] Add Waitlist model
- [ ] Create WaitlistService
- [ ] Create app/routers/waitlist.py
- [ ] Create WaitlistButton component
- [ ] Create WaitlistStatus component
- [ ] Update dashboard with waitlist section
- [ ] Add tests
- [ ] Create PR
- [ ] Merge PR

______________________________________________________________________

______________________________________________________________________

## CLI Backlog (Day 4-5 or Parallel)

### CLI PR #A: Auth & API Updates

**Depends on**: PR #1, #2, #3

- [ ] Create branch `feat/cli-auth-updates`
- [ ] Update base URL to `/api/v1/`
- [ ] Implement refresh token storage in config
- [ ] Add automatic token refresh before expiry
- [ ] Display password policy errors on registration
- [ ] Show account lockout message with remaining time
- [ ] Run tests: `pytest tests/test_cli/test_auth_cli.py`
- [ ] Create PR
- [ ] Merge PR

### CLI PR #B: Pagination Support

**Depends on**: PR #4

- [ ] Create branch `feat/cli-pagination`
- [ ] Add `--limit` flag to list commands
- [ ] Add `--cursor` flag for pagination
- [ ] Add `--all` flag with confirmation
- [ ] Display "Showing X of Y" in output
- [ ] Add `--sort` and `--order` flags
- [ ] Run tests
- [ ] Create PR
- [ ] Merge PR

### CLI PR #C: Recurring Reservations

**Depends on**: PR #6

- [ ] Create branch `feat/cli-recurring`
- [ ] Add `--recurrence` flag (daily/weekly/monthly)
- [ ] Add `--recurrence-end` flag
- [ ] Add `--days` flag for weekly recurrence
- [ ] Add `reservations cancel-series` command
- [ ] Run tests
- [ ] Create PR
- [ ] Merge PR

### CLI PR #D: Waitlist Commands

**Depends on**: PR #8

- [ ] Create branch `feat/cli-waitlist`
- [ ] Create `cli/commands/waitlist.py`
- [ ] Add `waitlist join` command
- [ ] Add `waitlist leave` command
- [ ] Add `waitlist status` command
- [ ] Add `waitlist list` command
- [ ] Add `waitlist accept` command
- [ ] Register in cli/main.py
- [ ] Run tests
- [ ] Create PR
- [ ] Merge PR

______________________________________________________________________

## Final Checklist

### Web Sprint Complete

- [ ] All 8 Web PRs merged
- [ ] Full test suite passes
- [ ] Frontend builds without errors

### CLI Sprint Complete

- [ ] All 4 CLI PRs merged
- [ ] CLI tests pass

### Release

- [ ] CHANGELOG.md updated
- [ ] Version bumped in pyproject.toml
- [ ] API docs updated
- [ ] E2E manual testing complete
- [ ] Release tag created

______________________________________________________________________

## Quick Commands

```bash
# Create new branch
git checkout -b feat/branch-name

# Run specific tests
pytest tests/test_api/test_auth.py -v

# Run all tests
mise run test

# Lint before commit
mise run lint

# Format code
mise run format

# Start dev environment
mise run dev
```

## Notes

_Use this space to track blockers, decisions, or anything else_

______________________________________________________________________
