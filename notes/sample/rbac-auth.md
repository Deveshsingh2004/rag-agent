# Multi-tenant RBAC and auth

## Auth surface

Multi-tenant SaaS auth with nine roles. JWT in HttpOnly cookies, refresh token rotation,
blacklist on logout, custom DRF permission classes scoped per organization.

## Why cookies

HttpOnly cookies reduce XSS token theft versus localStorage. Refresh rotation limits
replay if a refresh token leaks. Blacklist covers immediate revoke before expiry.

## Permissions

Hardcoded role checks were migrated to role-based permissions with custom rules per
role and org. Same lesson later applied in a fintech procurement module.
