# API Troubleshooting Runbook

## Overview

This runbook helps support teams investigate failed API calls using evidence that is safe to share. It focuses on endpoint details, HTTP method, status code, response body, timestamps, environment, and redacted request metadata.

## Key Concepts

- Good API troubleshooting starts with a reproducible failing request.
- Useful evidence includes endpoint path, HTTP method, request timestamp, response status, response body, environment, and request ID when available.
- Credentials, tokens, API keys, cookies, and signing secrets must be redacted before logs are shared.
- Failures should be separated into authentication, permission, validation, rate limit, network, and server categories.
- A single failed request should not trigger broad configuration changes until the failure category is understood.

## Common Questions

### What should a user send when an API call fails?

Ask for the endpoint path, method, status code, response body, timestamp, environment, and a redacted request example. Do not ask for full tokens or API keys.

### Why does a request fail only sometimes?

Intermittent failures can come from token expiry, rate limiting, network retries, temporary server errors, environment mismatch, or differences between request payloads.

### How should support compare requests?

Compare a known successful request against the failing request. Check endpoint, method, headers, content type, payload fields, account or environment, and response status.

## Troubleshooting

1. Confirm the endpoint path and HTTP method.
2. Confirm the user is calling the intended environment, such as test or production.
3. Check the status code and response body.
4. Confirm authentication and permission scope when the status is `401` or `403`.
5. Check payload format and required fields for `400` validation errors.
6. Add backoff for `429` and intermittent `5xx` errors.
7. Escalate with redacted logs, timestamp, endpoint, status code, and request ID.

## Best Practices

- Keep one clean failing example for investigation.
- Redact secrets before screenshots or logs are shared.
- Avoid repeated retries until the error category is understood.
- Include exact timestamps because backend logs are time-based.
