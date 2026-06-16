FROM postgres:16-alpine

# Custom init SQL is mounted at runtime via docker-compose volume.
# Place any additional seed scripts here if needed.
COPY init.sql /docker-entrypoint-initdb.d/01_init.sql
