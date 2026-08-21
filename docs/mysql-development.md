# MySQL 5.7 development environment

This Compose service is isolated from the existing Windows MySQL 8.0 service:

| Service | Host | Port | Database | User |
| --- | --- | ---: | --- | --- |
| Docker MySQL 5.7 | `127.0.0.1` | `3307` | `water_leak` | `water_app` |
| Windows MySQL 8.0 | unchanged | `3306` | unchanged | unchanged |

## Start and verify

Run these commands from the repository root:

```powershell
docker compose up -d mysql57
docker compose ps
docker compose logs --tail 100 mysql57
```

Wait until `docker compose ps` reports `(healthy)`.

## Application connection

The Python workflow should read its connection URL from an environment variable:

```text
DATABASE_URL=mysql+pymysql://water_app:water_workflow_app_dev_2026@127.0.0.1:3307/water_leak?charset=utf8mb4
```

For `mysql-connector-python`, use:

```python
config = {
    "host": "127.0.0.1",
    "port": 3307,
    "database": "water_leak",
    "user": "water_app",
    "password": "water_workflow_app_dev_2026",
}
```

Do not hard-code these credentials in application source. Load them from the
local `.env` file or process environment.

## Stop and restart

```powershell
docker compose stop mysql57
docker compose start mysql57
```

Stopping or recreating the container does not delete database data because it
is stored in the named volume `waterleak-mysql57-data`.

## Reset only the Docker development database

This operation permanently deletes the MySQL 5.7 development data and must not
be used as a normal stop command:

```powershell
docker compose down
docker volume rm waterleak-mysql57-data
docker compose up -d mysql57
```

The Windows MySQL 8.0 service on port `3306` is not managed by this Compose file.
