#!/bin/sh
# Written after the schema and seed scripts. The app waits until Postgres
# was started at or after this file, so it does not connect to the temporary
# server that runs these scripts.
touch "${PGDATA:-/var/lib/postgresql/data}/.sqlcoach-ready"
