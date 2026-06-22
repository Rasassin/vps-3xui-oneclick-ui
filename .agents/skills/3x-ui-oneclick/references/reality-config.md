# VLESS TCP Reality Reference

## Required Values

- protocol: `vless`
- network: `tcp`
- security: `reality`
- flow: `xtls-rprx-vision`
- encryption: `none`
- fingerprint: default `chrome`
- inbound port: default `443`
- SNI: default `www.microsoft.com`
- target: default `www.microsoft.com:443`

## Generated Values

- UUID: `uuidgen`
- shortId: `openssl rand -hex 8`
- X25519 keys: prefer 3x-ui API `getNewX25519Cert`; fallback to `xray x25519`

## Share Link

Use this shape:

```text
vless://UUID@HOST:PORT?type=tcp&security=reality&pbk=PUBLIC_KEY&fp=FINGERPRINT&sni=SNI&sid=SHORT_ID&spx=%2F&flow=xtls-rprx-vision&encryption=none#NODE_NAME
```

URL-encode query values and the fragment.

## Port Check

Before creating the inbound, check whether the Reality port is already listening. For port 443 failures, the UI should mention both local port occupation and possible VPS provider security group/firewall issues.

