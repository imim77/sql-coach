INSERT INTO practice.ports (id, name, country, latitude) VALUES
    (1, 'Bergen', 'Norway', 60.391),
    (2, 'Rotterdam', 'Netherlands', 51.922),
    (3, 'Hamburg', 'Germany', 53.551),
    (4, 'Antwerp', 'Belgium', 51.221),
    (5, 'Oslo', 'Norway', 59.913),
    (6, 'Gothenburg', 'Sweden', 57.709),
    (7, 'Aarhus', 'Denmark', 56.162),
    (8, 'Hull', 'United Kingdom', 53.745);

INSERT INTO practice.vessels (id, name, vessel_type, year_built, home_port_id) VALUES
    (1, 'Northline', 'coaster', 2014, 1),
    (2, 'Skagerrak', 'coaster', 2008, 5),
    (3, 'Fjord Mail', 'feeder', 2018, 1),
    (4, 'Elbe', 'feeder', 2011, 3),
    (5, 'Scheldt', 'tanker', 2004, 4),
    (6, 'Kattegat', 'coaster', 2016, 7);

INSERT INTO practice.voyages (
    id, vessel_id, departed_on, arrived_on, origin_port_id, destination_port_id
) VALUES
    (1, 1, '2024-03-01', '2024-03-03', 1, 2),
    (2, 1, '2024-03-10', '2024-03-12', 2, 3),
    (3, 1, '2024-04-02', '2024-04-04', 3, 1),
    (4, 2, '2024-02-14', '2024-02-16', 5, 6),
    (5, 2, '2024-05-01', '2024-05-04', 6, 8),
    (6, 3, '2024-01-20', '2024-01-22', 1, 7),
    (7, 3, '2024-06-01', NULL, 7, 2),
    (8, 4, '2024-03-15', '2024-03-18', 3, 4),
    (9, 4, '2024-04-20', '2024-04-22', 4, 3),
    (10, 4, '2024-07-01', '2024-07-02', 3, 5),
    (11, 5, '2024-02-01', '2024-02-05', 4, 8),
    (12, 5, '2024-03-22', '2024-03-26', 8, 2),
    (13, 5, '2024-08-01', '2024-08-06', 2, 4),
    (14, 1, '2024-01-05', '2024-01-08', 1, 5),
    (15, 2, '2024-01-11', '2024-01-12', 5, 1);

INSERT INTO practice.cargo (id, voyage_id, description, weight_tons, hazardous) VALUES
    (1, 1, 'grain', 120.0, false),
    (2, 1, 'timber', 40.5, false),
    (3, 2, 'chemicals', 15.0, true),
    (4, 3, 'fish', 80.0, false),
    (5, 4, 'paper', 60.0, false),
    (6, 5, 'machinery', 200.0, false),
    (7, 6, 'grain', 90.0, false),
    (8, 7, 'containers', 50.0, false),
    (9, 8, 'fuel', 300.0, true),
    (10, 9, 'steel', 150.0, false),
    (11, 10, 'fish', 70.0, false),
    (12, 11, 'chemicals', 25.5, true),
    (13, 12, 'grain', 110.0, false),
    (14, 13, 'oil', 400.0, false),
    (15, 14, 'timber', 30.0, false),
    (16, 15, 'paper', 45.0, false);

INSERT INTO practice.crew (id, name, role, vessel_id) VALUES
    (1, 'Ada Holm', 'master', 1),
    (2, 'Bo Lind', 'mate', 1),
    (3, 'Cleo Voss', 'engineer', 1),
    (4, 'Dan Berg', 'master', 2),
    (5, 'Eva Nilsen', 'mate', 2),
    (6, 'Finn Dahl', 'master', 3),
    (7, 'Gita Sol', 'engineer', 3),
    (8, 'Hans Meier', 'master', 4),
    (9, 'Ida Klein', 'cook', 4),
    (10, 'Jan Peeters', 'master', 5),
    (11, 'Kim De Smet', 'engineer', 5),
    (12, 'Lea Bak', 'master', 6),
    (13, 'Mo Iversen', 'mate', 6);
