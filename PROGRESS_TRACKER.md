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
- [ ] Merge PR

### PR #2: Refresh Tokens

- [ ] Create branch `feat/refresh-tokens`
- [ ] Add RefreshToken model to app/models.py
- [ ] Add refresh logic to app/auth.py
- [ ] Add /token/refresh endpoint
- [ ] Update frontend AuthContext
- [ ] Add axios interceptor for auto-refresh
- [ ] Add tests
- [ ] Run tests: `pytest tests/test_api/test_auth.py`
- [ ] Create PR
- [ ] Merge PR

### PR #3: Account Security

- [ ] Create branch `feat/account-security`
- [ ] Add LoginAttempt model
- [ ] Create app/utils/password.py
- [ ] Add lockout check to login flow
- [ ] Add PasswordStrengthMeter component
- [ ] Update login page with lockout message
- [ ] Add tests
- [ ] Run tests
- [ ] Create PR
- [ ] Merge PR

______________________________________________________________________

## Day 2: User Experience

### PR #4: Pagination & Filtering

- [ ] Create branch `feat/pagination-filtering`
- [ ] Add PaginatedResponse schema
- [ ] Update ResourceService with pagination
- [ ] Update ReservationService with pagination
- [ ] Create usePagination hook
- [ ] Update ResourceList component
- [ ] Update ReservationList component
- [ ] Add tests
- [ ] Create PR
- [ ] Merge PR

### PR #5: Notifications

- [ ] Create branch `feat/notifications`
- [ ] Add Notification model
- [ ] Create NotificationService
- [ ] Create app/routers/notifications.py
- [ ] Register router in main.py
- [ ] Create NotificationCenter component
- [ ] Create NotificationBadge component
- [ ] Create useNotifications hook
- [ ] Update dashboard with notification center
- [ ] Add tests
- [ ] Create PR
- [ ] Merge PR

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

- [ ] Create branch `feat/websocket-realtime`
- [ ] Create app/websocket.py
- [ ] Add WebSocket route to main.py
- [ ] Create WebSocketContext
- [ ] Create useWebSocket hook
- [ ] Add WS provider to layout
- [ ] Update dashboard with live updates
- [ ] Create LiveIndicator component
- [ ] Add tests
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
