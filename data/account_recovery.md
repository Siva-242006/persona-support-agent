# Account Recovery Guide

## Overview

This article helps support teams guide users who cannot access an account because they lost access to their recovery email, phone number, verification link, or sign-in method. The guidance follows common public account recovery practices: use the documented recovery flow first, avoid collecting secrets, and escalate identity-sensitive account changes.

## Key Concepts

- Account recovery should start from the service provider's official sign-in or account recovery page.
- Users may need access to a registered email address, phone number, recovery code, or other verification method.
- Verification links and codes can expire, so users may need to request a new one.
- Support should never ask users to share passwords, one-time codes, recovery codes, or full identity documents in ordinary chat.
- Account ownership changes, email changes, admin changes, account deletion, and access transfers require human verification.

## Common Questions

### What if the user cannot access the registered email?

Ask the user to try the documented account recovery flow. If they cannot access any registered recovery method, route the case to a human account reviewer for identity and ownership verification.

### Can support change the account email in chat?

No. Changing a sign-in email or recovery email is an account modification request. A human reviewer must verify identity and permissions before any change.

### What if the verification link expired?

The user should request a new verification or password reset link from the official recovery page and use the newest link.

## Troubleshooting

1. Ask the user to open the official account recovery or sign-in help page.
2. Confirm they are entering the correct email address, phone number, or account identifier.
3. Ask them to check spam, junk, filtered, and alternate inbox folders.
4. Ask them to request a new link or code if the previous one expired.
5. Ask them to try a supported browser if the recovery page does not load.
6. Escalate if recovery channels are unavailable or the user requests ownership, email, admin, deletion, or access changes.

## Best Practices

- Keep recovery instructions short and calm.
- Do not request passwords or verification codes.
- Do not promise account restoration before verification.
- Preserve the user's stated issue and available recovery methods in the handoff JSON.
