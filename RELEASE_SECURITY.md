# Release signing and Windows security

Personal Photo Toolkit must never instruct end users to disable Microsoft Defender, Smart App Control, Windows Application Control, Gatekeeper, or equivalent platform security controls.

## Public release policy

- Source/developer installs remain modular: core, `trip`, and `cleaner` dependencies are separate.
- Public binaries are built as editions so ordinary users do not run `pip` on their computer:
  - **Core** — Organizer only.
  - **Cleaner** — Organizer + Photo Cleaner.
  - **Trip** — Organizer + Trip Photo Filter.
  - **Full** — all features.
- AI model weights remain first-use downloads when licensing permits; user media stays local.
- Windows release binaries should be Authenticode-signed before publication.
- macOS releases should be Developer ID signed and notarized before being described as official signed releases.
- If signing credentials are not configured, CI artifacts are development/community builds and must not be described as signed.

## GitHub Actions secrets for Windows signing

Configure these repository secrets only in the GitHub repository settings. Never commit the certificate or password:

- `WINDOWS_CERTIFICATE_BASE64` — base64 encoded `.pfx` code-signing certificate.
- `WINDOWS_CERTIFICATE_PASSWORD` — password for that `.pfx`.

The workflow decodes the certificate only on the Windows runner, signs the executable with `signtool`, verifies the signature, then deletes the temporary certificate file.

A certificate must come from a trusted code-signing CA (or the organization’s approved signing service). Merely self-signing an executable does not give public users the same trust/reputation behavior.

## Managed computers

If organizational Application Control blocks a dependency, users should contact their IT administrator or use an approved/signed build. The project documentation must not recommend disabling the policy.
