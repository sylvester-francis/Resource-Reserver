# User Management

## Initial setup

The first admin account is created via the setup flow:

- `GET /setup/status` to check status
- `POST /setup/initialize` to create the initial admin user

## Reopening setup

If setup is already complete, you can reopen it with a token:

1. Set `SETUP_REOPEN_TOKEN` in your environment
1. Call `POST /setup/unlock` with header `X-Setup-Token`

## Roles and access

User access is controlled by roles. See `admin/roles.md` for role management endpoints.

## Approval workflows

Resources can require approval. Approval endpoints live under `/api/v1/approvals` and allow approvers to approve or reject requests.
