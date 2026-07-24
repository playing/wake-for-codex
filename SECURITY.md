# Security policy

## Scope

Security-sensitive areas include:

- microphone capture and audio retention;
- global hotkey injection;
- Codex Hook installation and merging;
- subprocess and model-download commands;
- log redaction and rotation;
- path validation during install and uninstall.

## Reporting

Use this repository's **Security → Report a vulnerability** flow. Do not open a
public issue containing exploit details, audio, prompts, local paths, credentials,
or other personal data. If Private Vulnerability Reporting is temporarily
unavailable, open a minimal issue asking the maintainer for a private contact
channel without including sensitive details.

## Invariants

- No raw audio, transcript, prompt, conversation, credential, or API key is stored.
- A wake detection may only trigger the configured Voice Chat hotkey.
- The launcher never sends a prompt or approves a Codex permission request.
- Hook installation preserves unrelated user hooks and creates a backup.
- Model archives are fetched only from the documented upstream URL and must match
  the pinned SHA-256 digest.
