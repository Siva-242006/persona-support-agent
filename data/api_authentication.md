# API Authentication Guide

## Overview

This article explains real-world HTTP API authentication patterns for support teams. It focuses on the `Authorization` request header, bearer token formatting, `401 Unauthorized` responses, and safe credential handling.

## Key Concepts

- The HTTP `Authorization` header is commonly used to send credentials for protected resources.
- Bearer token requests commonly use this structure: `Authorization: Bearer <access_token>`.
- The authentication scheme name, such as `Bearer`, appears before the credential value.
- `401 Unauthorized` means the request lacks valid authentication credentials for the target resource.
- Tokens and API keys are secrets. Users should redact them before sharing logs or screenshots.
- If a token expires, the user should generate a new token through the documented authentication flow.

## Common Questions

### What header is required for bearer token authentication?

Use the `Authorization` header with the bearer scheme:

`Authorization: Bearer <access_token>`

The token should not be placed in the URL or pasted into a support chat.

### Why does an API return `401 Unauthorized`?

Typical causes include a missing `Authorization` header, an expired token, an invalid token, credentials copied with extra whitespace, or credentials created for the wrong environment or account.

### Is `401` the same as `403`?

No. `401` points to missing or invalid authentication. `403` usually means the request was authenticated but the authenticated identity does not have permission for the resource.

## Troubleshooting

1. Confirm the request includes an `Authorization` header.
2. Confirm the value begins with `Bearer ` followed by one access token.
3. Remove extra spaces, quotes, line breaks, or copied characters.
4. Generate a new token if expiration is possible.
5. Confirm the token belongs to the correct account, environment, or application.
6. Redact secrets before sharing request examples with support.

## Best Practices

- Never expose full bearer tokens, API keys, passwords, or signing secrets.
- Use HTTPS for authenticated API traffic.
- Rotate credentials if a secret may have been exposed.
- Log status code, endpoint, timestamp, and request ID, but redact credential values.
