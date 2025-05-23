CREATE INDEX idx_submission_fast  ON submission (project_id, form_id, original_md5sum, sameas, submission_id);
CREATE INDEX idx_submission_last  ON submission (project_id, form_id, sameas, submission_dtime);
CREATE INDEX idx_fast_surveyid ON maintable (surveyid);