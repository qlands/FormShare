---
description: Submissions are the individual records sent to a form. This section explains how they flow into FormShare, how they are identified, and what states they can be in.
---

# Submissions

A **submission** is a single completed instance of an ODK form — for a household survey, one submission is one household; for an animal-tagging form, one submission is one animal. Submissions are the unit of data that FormShare collects, stores, cleans, and exports.

## Where do submissions come from?

FormShare can accept submissions from several sources:

* **ODK Collect** running on Android phones is by far the most common source. Each form in FormShare exposes an ODK Collect–compatible endpoint, and a QR code on the form details page configures Collect in one scan.
* **Enketo Express** (a web-based form-filling tool) can be used when devices cannot run ODK Collect, or for testing through a browser. Enketo is provided through an optional FormShare plugin.
* **Imports from other systems** are supported for forms that already have data elsewhere — for example, projects migrating from FormShare 1.0 or from ODK Central. See "[Import external data](import-external-data.md)" for the available source types.
* **API submissions** are also possible — assistants can POST data programmatically using their API key. This is most often used when migrating or when integrating FormShare with another platform.

Regardless of the source, every submission is attributed to an [assistant](../tasks/) so that FormShare can record *who* contributed the record.

## The two storage modes

How a submission is stored depends on the form's stage (see "[Forms](../forms/)" for the full picture):

* **Forms in the testing stage** store every submission as a JSON file inside the form's working directory. Testing-stage submissions are considered disposable — replacing the form deletes them. They exist so you can validate the form on real devices before committing to a database schema.
* **Forms with a repository** store every submission as relational data inside a dedicated MySQL database (the repository). Submission media (photos, audio, video, signatures) are saved as files; everything else lives as rows in the data, lookup, and multi-select tables described in "[How does FormShare stores my data?](../repositories/how-does-formshare-stores-my-data.md)".

The behavior of every feature in FormShare — exports, cleaning, audit log, sensitive-field masking — depends on whether the form has a repository.

## Submission identity

Every submission FormShare receives is assigned a unique **submission ID** (`rowuuid`) the moment it lands on the server. This ID is preserved across form-version merges and is the canonical handle for the submission, no matter what table its data ends up in.

The submission ID lets FormShare:

* Locate every row across every table of the repository that belongs to a given submission (a single submission with repeats produces several rows).
* Move submissions between states (database, error log, log entries) without losing traceability.
* Reference a submission from the API, from the [audit log](../../data-management/cleaning/in-a-repository/audit-log.md), or from the file system holding media attachments.

> Add screenshot of a submission detail panel showing the submission ID prominently.

In addition to the submission ID, FormShare stores ODK Collect metadata (start time, end time, device ID, instance ID) for every submission. This metadata is available in exports and is what powers the timeline-style activity statistics you see on the dashboard.

## Submission states

In a form with a repository, every submission is in one of three states:

* **In the database**: The submission passed the repository's integrity rules (no duplicate primary key, no missing required field, no unknown lookup option) and is stored as relational data. This is the normal, "clean" state.
* **In the error log**: Something prevented the submission from entering the database — most often a duplicate primary key, a missing required field, or a value that doesn't match the form's option list. The submission sits in the error log until somebody fixes it. See "[Submissions with errors](../../data-management/cleaning/submissions-with-errors.md)".
* **In the log entries** (disregarded): The submission was either set aside on purpose (it was a test record, a bad entry an enumerator wants to keep for the audit trail, or a duplicate that should be kept for accountability) or moved out of the database for manual review. Log entries are kept indefinitely as auditable traces; they don't show up in exports and don't count toward submission totals.

Submissions can be moved between states from the **Manage submissions** screen — see "[Working with submissions](../../data-management/cleaning/working-with-submissions.md)".

{% hint style="info" %}
**FormShare doesn't physically delete submission data.** When you delete a submission, FormShare moves it to the log entries and marks it deleted. The underlying rows in MySQL and the media files on disk remain in place. This is by design — it preserves the audit trail even after data has been removed from the analytical dataset.
{% endhint %}

## Media files

Submissions often carry attached media — photos, signatures, audio recordings, short videos. FormShare stores each media file on disk under the form's directory, indexed by submission ID. Media is delivered separately from the relational data:

* Exports of the data (CSV, JSON, Excel) reference media files by filename.
* The "Download submitted media" option in the form details produces a Zip with every media file, organized into one folder per submission ID.

## What's next

* "[Import external data](import-external-data.md)" covers loading submissions from JSON, XML, or plugin-provided sources.
* "[Working with submissions](../../data-management/cleaning/working-with-submissions.md)" covers the day-to-day operations on submissions (delete, disregard, restore).
* "[Submissions with errors](../../data-management/cleaning/submissions-with-errors.md)" covers what causes the error log and how to drain it.
* "[The audit log](../../data-management/cleaning/in-a-repository/audit-log.md)" covers the change-history view for every cleaned submission.
