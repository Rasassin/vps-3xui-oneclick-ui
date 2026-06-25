# Publish Now

This is the shortest path to publish the current open-source MVP. Do not paste
VPS passwords, tokens, signing secrets, node links, QR images, or panel
credentials into GitHub.

## 1. Refresh Local Release Pack

```bash
npm run external:preflight
npm run product:check
```

Expected local status:

- Open-source portable release: go.
- GitHub Release upload folder: `dist/github-release-upload-v1.55.0`.
- Upload file count: 33 files.
- Remaining blockers after this step are external evidence only.

## 2. Push With GitHub Desktop

Open GitHub Desktop, select this repository, review the changed files, commit,
and push.

After the push, record evidence:

```bash
npm run external:publish-evidence
```

If GitHub network checks are still blocked locally, use the manual fallback:

```bash
python3 scripts/record_external_release_evidence.py --type github_desktop_push --status pass --summary 'Branch pushed with GitHub Desktop.' --notes 'No secrets included.'
```

## 3. Create GitHub Release

Create release tag `v1.55.0` on GitHub. Use `dist/GITHUB_RELEASE_v1.55.0.md`
as release notes.

Upload every file from:

```text
dist/github-release-upload-v1.55.0
```

Use this checklist while uploading:

```text
dist/GITHUB_RELEASE_UPLOAD_MANIFEST_v1.55.0.md
```

After upload, record evidence:

```bash
npm run external:publish-evidence
npm run external:finalize
```

If GitHub network checks are still blocked locally, use the manual fallback:

```bash
python3 scripts/record_external_release_evidence.py --type github_release_upload --status pass --summary 'Expected GitHub Release assets were uploaded.' --url 'https://github.com/daiyujun/vps-3xui-oneclick-ui/releases/tag/v1.55.0' --notes 'No secrets included.'
npm run external:finalize
```

## 4. Optional Later Work

These are not required for the open-source portable MVP, but are required
before claiming a fully signed public desktop product:

- Ubuntu 22.04 VPS compatibility evidence.
- Debian 12 VPS compatibility evidence.
- macOS signing and notarization evidence.
- Windows signing evidence.
- Signed artifact validation evidence.

## Final Local Check

```bash
npm run external:preflight
npm run external:dashboard
npm run product:check
```

