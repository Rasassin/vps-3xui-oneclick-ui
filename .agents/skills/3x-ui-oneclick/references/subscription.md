# Subscription Reference

3x-ui subscription URLs depend on panel version and settings. The common modern shape is tied to the client `subId`, often:

```text
http://HOST:SUB_PORT/sub/SUB_ID
```

Some setups use HTTPS, custom subscription ports, or a configured subscription URI path from the x-ui database settings such as `subPort`, `subPath`, `subCertFile`, `subKeyFile`, and `subURI`. Recover these settings first, then build likely URLs from the generated `subId`; verify with `curl` and accept only HTTP 2xx with non-empty body.

## Failure Policy

Subscription generation is best-effort:

- If subscription link and QR are generated, display both.
- If subscription link fails, do not fail deployment if VLESS link and QR exist.
- Write an empty `subscription-link.txt` if missing.
- Remove stale `subscription-qr.png` when subscription fails.
- UI message must be:

```text
订阅链接生成失败，但单节点 VLESS 二维码已经生成，可直接扫码使用。
```
