"""What a form's testing left, recorded before the form gets a repository and
dealt with after it has one (products/repository and products/merge).

Until it has a repository, a form keeps each testing submission as files in
forms/<directory>/submissions/ -- <id>.xml, <id>.json, <id>.original and a
directory <id>/ with the media -- and as a document of the dataset index whose
id is <id>. When the repository is built, or a new version is merged into one,
the owner chooses to discard them or to import them into it.

Both tasks used to take whatever the directory and the index held once the
form had its schema. By then the form takes real submissions, and one that
arrived in between went with the testing data: its row stayed in the
repository and its XML, JSON and index document were deleted, or, caught half
way, the device got a 500. That is how CI build 880 (2026-10-16) failed: the
merged version's first submission arrived while the merge task updated the
dictionary. So what testing left is recorded while the form takes no
submission, before the commit that hands it its schema, and only what was
recorded is discarded or imported.
"""

import glob
import logging
import os
import shutil

from formshare.processes.elasticsearch.repository_index import (
    delete_datasets_by_id,
    get_dataset_ids,
)
from formshare.processes.logging.loggerclass import SecretLogger

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")

# Directories of the submissions directory that are not a submission's
KEPT_DIRECTORIES = ("logs", "maps")


class RecordedTestingData:
    """The files, media directories and index documents of a form's testing
    submissions, as record_testing_data found them."""

    def __init__(self, project_id, form_id, files, directories, submission_ids):
        self.project_id = project_id
        self.form_id = form_id
        self.files = files
        self.directories = directories
        self.submission_ids = submission_ids

    @property
    def json_files(self):
        """The testing submissions' JSON files, which an import takes."""
        return [a_file for a_file in self.files if a_file.endswith(".json")]

    def forget_documents(self, settings):
        """Deletes the testing submissions' documents from the dataset index.
        An import indexes them again, so it comes after this."""
        delete_datasets_by_id(
            settings, self.project_id, self.form_id, self.submission_ids
        )

    def remove_files(self):
        """Removes the testing submissions' files and media directories."""
        for a_file in self.files:
            try:
                os.remove(a_file)
            except Exception as e:
                log.error(str(e))
        for a_directory in self.directories:
            try:
                shutil.rmtree(a_directory)
            except Exception as e:
                log.error(str(e))


def record_testing_data(settings, odk_dir, form_directory, project_id, form_id):
    """What the form's testing left. Call it while the form takes no
    submission and has not been handed its schema yet: whatever comes after
    is a real submission, and is not in the record."""
    submissions = os.path.join(odk_dir, "forms", form_directory, "submissions")
    files = sorted(glob.glob(os.path.join(submissions, "*.*")))
    directories = sorted(
        a_directory
        for a_directory in glob.glob(os.path.join(submissions, "*/"))
        if os.path.basename(os.path.normpath(a_directory)) not in KEPT_DIRECTORIES
    )
    # The documents come from the index and from the files' names both: a
    # document the index took in the last second is not searchable yet, and
    # one whose files are gone is still the form's testing.
    submission_ids = {
        os.path.basename(os.path.normpath(a_path)).split(".")[0]
        for a_path in files + directories
    }
    try:
        submission_ids.update(get_dataset_ids(settings, project_id, form_id))
    except Exception as e:
        log.error(
            "The index documents of form {} in project {} could not be read. "
            "Only those of its testing files will be deleted. Error: {}".format(
                form_id, project_id, str(e)
            )
        )
    return RecordedTestingData(
        project_id, form_id, files, directories, sorted(submission_ids)
    )
