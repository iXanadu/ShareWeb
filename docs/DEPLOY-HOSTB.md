# Share on WebOne — share.c52.com

Same shape as other c52 FastAPI apps. nginx + TLS are the website-setup path.
This repo only owns the app unit.

| | |
| --- | --- |
| Host | WebOne |
| Path | `/var/www/share.c52.com/prod` |
| User | `share_user` |
| Unit | `uvicorn_share_c52_prod` |
| Bind | `127.0.0.1:8021` |
| Public | `https://share.c52.com` → nginx → that port |
| Venv | `/usr/local/pyenv/versions/share-3.13` |
| Files | `/var/lib/share/files` and `/var/lib/share/tmp` (same filesystem) |
| Upload cap | 50 MiB/file, 64 MiB/artifact — matches nginx `client_max_body_size 64M` |

**Not Caddy.** Spec Part 2 names Caddy; WebOne is nginx like every other c52 app. FastAPI serves artifacts behind nginx for this deploy.

## After the human has folder + cert

```bash
ssh hostb
cd /var/www/share.c52.com/prod
git pull
# .env / .keys owned by share_user, chmod 600
# SHARE_HOST=share.c52.com
# SHARE_BIND_HOST=127.0.0.1
# SHARE_PORT=8021
# SHARE_FILE_ROOT=/var/lib/share/files
# SHARE_TMP_ROOT=/var/lib/share/tmp
./scripts/install.sh    # first time
./scripts/restart.sh    # later pulls
curl -sf http://127.0.0.1:8021/health
curl -sf https://share.c52.com/health
```

Do not run `./scripts/install.sh` from hosta — it refuses unless Linux.
