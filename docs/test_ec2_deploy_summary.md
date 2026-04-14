# Test EC2 Deploy Summary (`test.mirrulations.org`)

## What was done

1. Connected to test EC2 instance `i-05f5e833d512d42b7` (`100.24.243.117`, `t3.large`).
2. Worked from repo directory `~/SEARCHTEST_mirrulations`.
3. Confirmed deploy files were already set to `test.mirrulations.org`:
   - `prod_deploy.sh` had `DOMAIN="test.mirrulations.org"`.
   - `mirrsearch.service` cert/key paths referenced `test.mirrulations.org`.
4. Ran `./prod_deploy.sh`.
5. Hit DB bootstrap failure because `db/setup_postgres.sh` is Homebrew/macOS-specific (`brew` not available on Amazon Linux).
6. Manually initialized Postgres DB using SQL files copied to `/tmp` (because `postgres` user could not read files directly under `/home/ec2-user/...`).
7. Fixed localhost Postgres auth to allow password-based login and set `postgres` password.
8. Re-ran deploy; frontend built successfully, existing certificate was kept, and service started.
9. Verified service health and HTTPS response:
   - `systemctl status mirrsearch` => active/running
   - `curl -Ik https://test.mirrulations.org` => `HTTP/1.1 200 OK`

## Key issue and resolution

- **Issue:** `prod_deploy.sh` may call `./db/setup_postgres.sh`, which currently assumes Homebrew.
- **Resolution:** Create DB manually on Linux and ensure `PGPASSWORD=postgres psql -h localhost -U postgres` works so deploy check passes and brew script is skipped.

## Commands that worked

```bash
cd ~/SEARCHTEST_mirrulations

cp db/schema-postgres.sql /tmp/schema-postgres.sql
cp db/sample-data.sql /tmp/sample-data.sql
chmod 644 /tmp/schema-postgres.sql /tmp/sample-data.sql

sudo -u postgres createdb mirrulations 2>/dev/null || true
sudo -u postgres psql -d mirrulations -f /tmp/schema-postgres.sql
sudo -u postgres psql -d mirrulations -f /tmp/sample-data.sql

sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"

PGDATA=$(sudo -u postgres psql -t -A -c "SHOW data_directory" | tr -d '[:space:]')
sudo sed -i.bak -E 's#^(host[[:space:]]+all[[:space:]]+all[[:space:]]+127\.0\.0\.1/32[[:space:]]+).*$#\1md5#' "$PGDATA/pg_hba.conf"
sudo sed -i.bak -E 's#^(host[[:space:]]+all[[:space:]]+all[[:space:]]+::1/128[[:space:]]+).*$#\1md5#' "$PGDATA/pg_hba.conf"
sudo systemctl restart postgresql || true

PGPASSWORD=postgres psql -h localhost -U postgres -lqt postgres | grep -w mirrulations

./prod_deploy.sh
sudo systemctl status mirrsearch --no-pager
curl -Ik https://test.mirrulations.org
```

## Notes

- `npm WARN EBADENGINE` warnings were non-blocking in this run; frontend build still succeeded.
- Certbot prompt appeared because certificate already existed and was not due for renewal; selecting `1` ("Keep existing certificate") allowed deploy to continue.
