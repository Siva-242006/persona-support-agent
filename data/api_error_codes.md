# API Error Code Guide

## Overview

This article helps support teams explain common HTTP API error categories and choose the right troubleshooting path. It is based on standard HTTP status code behavior used by public APIs.

## Key Concepts

- `400 Bad Request` usually means the request syntax, parameters, or body are invalid.
- `401 Unauthorized` means valid authentication credentials were not supplied or were not accepted.
- `403 Forbidden` means the request was understood but the authenticated user or token is not permitted to access the resource.
- `404 Not Found` means the endpoint or requested resource could not be found.
- `409 Conflict` means the request conflicts with the current state of a resource.
- `429 Too Many Requests` means the client is sending requests too quickly or has exceeded a rate limit.
- `5xx` responses usually indicate a server-side or upstream service issue.

## Common Questions

### What is the difference between `401` and `403`?

`401` is an authentication problem. `403` is a permissions or authorization problem after the request identity is known.

### What information should a user provide for an API error?

Ask for the endpoint path, HTTP method, status code, response body, timestamp, environment, and a redacted request example.

### Should rate limit errors be retried?

Yes, but retries should use delay or backoff. Repeating the same request rapidly can make rate limiting worse.

## Troubleshooting

1. Identify the status code family: `4xx` usually points to request/client issues, while `5xx` points to service-side issues.
2. Read the response body for validation messages or error details.
3. Confirm the endpoint, method, and required parameters.
4. Check credentials and permission scope for `401` and `403`.
5. Use slower retry behavior for `429` and intermittent `5xx` responses.
6. Escalate repeated `5xx` errors with timestamps, request IDs, and endpoint details.

## Best Practices

- Do not treat every API error as an authentication issue.
- Use the status code to decide the next action.
- Preserve exact timestamps for log investigation.
- Redact credentials before sharing request or response samples.
