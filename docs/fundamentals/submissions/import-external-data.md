---
description: Load submissions into a FormShare repository from another system — FormShare 1.0, ODK Central, or any platform supported by an installed plugin.
---

# Import external data

When a form already has data elsewhere — because you are migrating from another platform, restoring a backup, or consolidating multiple sources — FormShare can import that data directly into the form's repository instead of having you re-collect it.

{% hint style="info" %}
**Imports require a repository.** External data can only be imported into a form that already has a repository. If your form is still in the testing stage, [create a repository](../forms/#create-a-repository) first. Imports merge into the existing data; they don't replace it.
{% endhint %}

## How to import

From the form details page, click **Import external data**. The import page appears.

> Add screenshot of the "Import data" form with the three fields (Source type, Assistant, Data file).

You need to provide:

* **Source type**: The format of the file you are about to upload. Available options:
  * **FormShare 1.0 (JSON / Zip)** — submissions exported from FormShare 1.0 as JSON files, packaged in a Zip.
  * **ODK Collect XML data files (Zip)** — raw XML instances exactly as ODK Collect produces them, packaged in a Zip. This is the format used to migrate from ODK Central and from any other Aggregate-compatible server.
  * **Additional types** may appear here if your FormShare instance has plugins installed that add custom importers. Each plugin documents its own expected file layout.
* **Assistant**: Pick which [assistant](../tasks/) FormShare should record as the submitter of the imported records. Every submission in a FormShare repository is attributed to an assistant; for imports, you typically create a dedicated assistant like "migration" so the imports are easy to spot in the audit log.
* **Data file**: The Zip file containing the data. For FormShare 1.0 imports the Zip can contain individual JSON files; for ODK XML imports the Zip must contain XML files and their media attachments.

Click **Import data**. FormShare creates a background task and takes you to the form details page on the **Tasks** tab, where you can watch the import progress in real time.

## What happens during an import

FormShare processes each submission in the Zip in turn, applying the same rules a live submission would face:

1. The data is validated against the form's structure. Missing required fields, unknown lookup options, or out-of-range values cause the submission to land in the [error log](../../data-management/cleaning/submissions-with-errors.md) instead of the database.
2. Duplicate primary keys are blocked — if a primary-key value already exists in the database, the new submission goes to the error log so you can decide what to do.
3. Each accepted submission is given a fresh FormShare **submission ID** (`rowuuid`). It is then split across the data, lookup, and multi-select tables exactly like a live submission, so imported data is indistinguishable from data collected through ODK Collect.
4. Media files referenced by each submission are unpacked into the form's media directory under the new submission ID.

{% hint style="warning" %}
**The Zip must be a Zip.** For the ODK XML and FormShare 1.0 source types, FormShare expects a Zip archive. Other formats — `.tar.gz`, `.7z`, a folder, or a single XML/JSON file uploaded directly — will be rejected with an error.
{% endhint %}

## Tracking the import

The form details page has a **Tasks** tab listing every background operation against the form, including imports. Each task shows:

* The product code (e.g. `fs1import` for FormShare 1.0 imports, `xmlimport` for ODK XML imports, plugin-specific codes for plugin-provided importers).
* Status: running, completed, or failed.
* A live progress log streamed from the worker as the import advances.

When the import finishes, the submission count on the form details page updates. If any submissions ended up in the error log, the "With error" badge on the form will reflect the new count — review those from the [submissions with errors](../../data-management/cleaning/submissions-with-errors.md) page and clean them up.

## When *not* to use import

* If you only need to load a handful of records, it is often easier to submit them through ODK Collect using a test device.
* If your source data is in CSV or Excel format, you cannot import it directly — convert it to FormShare 1.0 JSON or to ODK XML first, or ask whether a plugin can be written for your specific source.
* Imports cannot create test-stage submissions; they always go directly into the repository.
