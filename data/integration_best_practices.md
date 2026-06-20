# Integration Best Practices

## Overview

This article gives practical, real-world guidance for technical customers integrating with an API. It focuses on environment separation, request logging, credential safety, retry behavior, and escalation evidence.

## Key Concepts

- Stable integrations separate test and production environments.
- Credentials should match the environment and account being accessed.
- Request logs should include endpoint, method, status code, timestamp, and request ID when available.
- Sensitive values such as tokens, API keys, cookies, passwords, and signing secrets should be redacted.
- Retry logic should use backoff for temporary failures and rate limits.
- Configuration changes should be tracked so recent deployment or credential changes can be reviewed.

## Common Questions

### What should a technical customer check first?

Check the base URL, environment, HTTP method, `Authorization` header, content type, request body, status code, and response body.

### What should be logged?

Log request metadata and response details. Do not log full credentials, payment card numbers, passwords, verification codes, or secrets.

### When should support escalate an integration issue?

Escalate when the customer provides redacted request details and the issue cannot be explained by authentication, payload validation, permissions, rate limits, or documented behavior.

## Troubleshooting

1. Confirm the correct environment is being used.
2. Verify the credential belongs to the account or application being accessed.
3. Confirm required headers and content type are present.
4. Compare a successful request with the failing request.
5. Review recent deployments, configuration changes, and credential rotations.
6. Escalate with redacted logs, timestamps, endpoint, method, and observed status code.

## Best Practices

- Use small, repeatable test requests.
- Keep test and production credentials separate.
- Redact secrets before sharing logs.
- Add retry backoff for temporary failures.
