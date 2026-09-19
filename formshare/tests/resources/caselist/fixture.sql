SET NAMES utf8mb4;
CREATE TABLE cases (rowuuid varchar(80) NOT NULL, hh_name varchar(255), status varchar(60), visits bigint, area decimal(9,3), lat double, registered datetime, born date, notes text, PRIMARY KEY (rowuuid)) ENGINE = InnoDB CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
INSERT INTO cases VALUES ('11111111-1111-4111-8111-111111111111','Maria','registered',3,1.500,12.0,'2026-01-01 09:00:00','1990-05-17','plain');
INSERT INTO cases VALUES ('22222222-2222-4222-8222-222222222222','Perez, Maria "La China"',NULL,0,0.000,-1.2921,'2026-12-31 23:59:59',NULL,'a line\nbreak and a\r\nCRLF');
INSERT INTO cases VALUES ('33333333-3333-4333-8333-333333333333','José Ñandú 東京','',-7,NULL,1e-05,NULL,'2000-02-29','trailing space ');
INSERT INTO cases VALUES ('44444444-4444-4444-8444-444444444444','','x',1234567890123,99999.999,1e+16,'2026-06-15 00:00:00','2026-06-15','"quoted"');
INSERT INTO cases VALUES ('55555555-5555-4555-8555-555555555555',' leading','y',NULL,-0.500,NULL,NULL,NULL,',');
INSERT INTO cases VALUES ('66666666-6666-4666-8666-666666666666','tab\there','z',1,12.000,123456.789,'2026-01-01 00:00:01','1970-01-01','');
