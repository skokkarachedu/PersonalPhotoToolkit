# Releases

## v2.0.1

- Trip Filter and Photo Cleaner now preserve videos separately under `Videos/Unfiltered`.
- Windows source setup now uses an isolated `.venv`.
- Windows setup prefers Python 3.11/3.12 and fails clearly instead of printing a false success after pip errors.
- This avoids common global-package conflicts such as `WinError 5` on `cv2.pyd`.

# Desktop releases

This repository can build standalone desktop packages for Windows, macOS and Linux.

## Build all platforms with GitHub Actions

After pushing the repository to GitHub:

1. Open **Actions**.
2. Select **Build desktop releases**.
3. Click **Run workflow**.
4. Download the build artifacts when the workflow finishes.

Artifacts:

```text
PersonalPhotoToolkit-Windows.zip
PersonalPhotoToolkit-macOS.zip
PersonalPhotoToolkit-Linux.tar.gz
```

These contain packaged applications, so end users do not need to install Python.

## Create a public release

Create a version tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions will build all three operating-system versions and attach them to a GitHub Release.

## Build locally

### Windows

```powershell
.\build_scripts\build-windows.ps1
```

Output:

```text
dist\PersonalPhotoToolkit.exe
```

### macOS

Run on an actual Mac:

```bash
chmod +x build_scripts/build-macos.sh
./build_scripts/build-macos.sh
```

Output:

```text
dist/Personal Photo Toolkit.app
```

### Linux

```bash
chmod +x build_scripts/build-linux.sh
./build_scripts/build-linux.sh
```

Output:

```text
dist/PersonalPhotoToolkit
```

## Signing

The current builds are unsigned.

For polished public distribution:

- Windows: sign the executable with a code-signing certificate.
- macOS: sign and notarize the application with an Apple Developer certificate.
- Linux: optionally publish SHA-256 checksums or GPG signatures.

Never commit signing certificates or passwords to the repository. Store them in GitHub Actions secrets.

## File size

The full version includes PyTorch and Transformers for the AI cleaner, so the release files can be large.

A useful future contribution would be two editions:

```text
Lite  = year organizer + trip filter
Full  = all three tools including AI cleaner
```

## v2.0 privacy-first AI behavior

The full desktop build packages the Python/runtime dependencies needed by the three tools. Large optional model weights are not bundled. The UI asks before the first Trip Filter or Photo Cleaner model download. `PRIVACY.md` explains local processing and face-recognition considerations.
