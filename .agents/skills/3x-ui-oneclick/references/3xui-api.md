# 3x-ui API Reference

Primary upstream:

- GitHub: https://github.com/MHSanaei/3x-ui
- Install script: https://raw.githubusercontent.com/MHSanaei/3x-ui/master/install.sh
- API docs are also exposed by the panel Swagger in recent versions.

## Login

Use local panel URL from the VPS:

```bash
curl -c cookie.txt -X POST "$PANEL_URL/login" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode "username=$PANEL_USER" \
  --data-urlencode "password=$PANEL_PASS"
```

Treat failed login as `XUI_API_FAILED`.

## Common API Paths

- `GET /panel/api/inbounds/list`
- `GET /panel/api/inbounds/get/:id`
- `POST /panel/api/inbounds/add`
- `POST /panel/api/inbounds/update/:id`
- `POST /panel/api/inbounds/del/:id`
- `GET /panel/api/server/getNewUUID`
- `GET /panel/api/server/getNewX25519Cert`

Send session cookies after login. Include `X-Requested-With: XMLHttpRequest` for API calls.

## Add Inbound

The add inbound endpoint accepts a JSON object where some nested settings are JSON strings:

- `protocol`: `vless`
- `port`: user-selected Reality port
- `settings`: stringified object containing `clients`, `decryption`, `fallbacks`
- `streamSettings`: stringified object containing TCP + Reality settings
- `sniffing`: stringified object

If the API response is not JSON or `.success` is not true, surface `INBOUND_CREATE_FAILED`.

## Recovery

After install, first read `/etc/x-ui/install-result.env`. If missing or incomplete, recover what is possible from `/etc/x-ui/x-ui.db` settings and users tables. If credentials cannot be recovered and login fails, stop with `XUI_API_FAILED`.

