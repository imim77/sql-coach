CREATE SCHEMA practice;

CREATE TABLE practice.ports (
    id integer PRIMARY KEY,
    name text NOT NULL,
    country text NOT NULL,
    latitude numeric(6, 3) NOT NULL
);

CREATE TABLE practice.vessels (
    id integer PRIMARY KEY,
    name text NOT NULL,
    vessel_type text NOT NULL,
    year_built integer NOT NULL,
    home_port_id integer NOT NULL REFERENCES practice.ports (id)
);

CREATE TABLE practice.voyages (
    id integer PRIMARY KEY,
    vessel_id integer NOT NULL REFERENCES practice.vessels (id),
    departed_on date NOT NULL,
    arrived_on date,
    origin_port_id integer NOT NULL REFERENCES practice.ports (id),
    destination_port_id integer NOT NULL REFERENCES practice.ports (id)
);

CREATE TABLE practice.cargo (
    id integer PRIMARY KEY,
    voyage_id integer NOT NULL REFERENCES practice.voyages (id),
    description text NOT NULL,
    weight_tons numeric(8, 1) NOT NULL,
    hazardous boolean NOT NULL
);

CREATE TABLE practice.crew (
    id integer PRIMARY KEY,
    name text NOT NULL,
    role text NOT NULL,
    vessel_id integer NOT NULL REFERENCES practice.vessels (id)
);

CREATE ROLE student LOGIN PASSWORD 'student';

GRANT CONNECT ON DATABASE sqlcoach TO student;
GRANT USAGE ON SCHEMA practice TO student;
GRANT SELECT ON ALL TABLES IN SCHEMA practice TO student;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

ALTER ROLE student SET search_path TO practice;
