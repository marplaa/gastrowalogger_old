CREATE TABLE sensors (
  id integer primary key,
  label text,
  type text,
  vendor text,
  author text,
  description text,
  alias text,
  email text,
  address integer,
  version text
);

CREATE TABLE active (
  sensor integer primary key autoincrement,
  FOREIGN KEY(sensor) REFERENCES sensors(id)
);

CREATE TABLE consumptions (
  id integer primary key autoincrement,
  sensor integer,
  'timestamp' INTEGER not null,
  'count' INTEGER not null,
  FOREIGN KEY(sensor) REFERENCES sensors(id)
);

CREATE TABLE notes (
  consumption integer primary key,
  note text,
  FOREIGN KEY(consumption) REFERENCES consumptions(id)
);

CREATE TABLE prices (
  id integer primary key autoincrement,
  timestamp_from integer not null,
  amount real not null
);

CREATE TABLE readings (
  id integer primary key autoincrement,
  sensor integer,
  'timestamp' INTEGER not null,
  reading real not null,
  note text,
  FOREIGN KEY(sensor) REFERENCES sensors(id)
);

CREATE TABLE weather (
  id integer primary key autoincrement,
  'timestamp' integer not null,
  avg_temp real,
  precip_mm real
);

