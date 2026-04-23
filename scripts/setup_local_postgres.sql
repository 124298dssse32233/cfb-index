-- Run this in pgAdmin while connected as postgres.
-- Change the password if you want, but keep it URL-friendly.

CREATE ROLE cfb_app WITH LOGIN PASSWORD 'cfb_dev_password_123';

CREATE DATABASE cfb_rankings OWNER cfb_app;

GRANT ALL PRIVILEGES ON DATABASE cfb_rankings TO cfb_app;

-- Optional: verify the server port in the same query tool.
SHOW port;
