INSERT INTO maintable (surveyid,originid,_submitted_by,_xform_id_string,_submitted_date,_geopoint,hid,fname,fsex,age,income,lastdate,lastdatetime,lasttime,crop,gps,rowuuid)  VALUES ('1e5675a2-4a2b-4bce-8a14-2b832d9e00b2','ODKTOOLS 2.0','cquiros','justtest','2020-03-21 18:05:55','9.8874643 -83.6563825 0.0 20.0','003','Flor','2','85','25000.0','2020-03-21','2020-03-21 18:04:00','2019-01-01 18:04:00','1','9.8874643 -83.6563825 0.0 20.0','6560748e-f2ee-4e3e-b76b-2001218fc016');
INSERT INTO maintable_msel_crop(hid,crop,rowuuid)  VALUES ('003','1','ded2b2e6-29a5-4196-853d-a8ad31350952');
INSERT INTO rpt_crops (hid,rpt_crops_rowid,sel_crop,crop_use,rowuuid)  VALUES ('003','1','1','1','3108d30b-4cf7-45c0-9981-769d1671b588');
INSERT INTO rpt_crops_msel_crop_use(hid,rpt_crops_rowid,crop_use,rowuuid)  VALUES ('003','1','1','2e974651-174c-499d-9e93-9d5a3f6ed430');
INSERT INTO rpt_usage (hid,rpt_crops_rowid,rpt_usage_rowid,sel_use,amount,market,rowuuid)  VALUES ('003','1','1','1','5866.0','1','9bf13820-2b90-437e-99fa-64ac1f9635e3');
INSERT INTO rpt_usage_msel_market(hid,rpt_crops_rowid,rpt_usage_rowid,market,rowuuid)  VALUES ('003','1','1','1','6d797b69-b2cf-4b4c-91f8-16c72d8a860a');
