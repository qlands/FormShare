# Walking the offline entity workflow by hand

Register a case, follow it up, and see the case identity the *device* minted end
up as the row's `rowuuid` — which is what lets a case registered offline be
followed up before it has ever reached the server.

**Audience:** whoever wants to see this work without reading the code.

**Before you start.** The deployment has to be able to serve entities at all:
`odktools.supports_entities = true` in the ini, pointing `odktools.path` at a
**RSTools** build from `main_3.0_entities` or later. ODKTools cannot do this. The
`project_entities` column needs its alembic migration applied. Celery has to be
running, or repositories never finish building.

**The project code has to be `demo`.** FormShare derives the case list name from
it — `demo` gives `demo_cases`, and the forms here select from `demo_cases.csv`.
Any other code and the follow-up will be refused at upload, which is the check
working, not a bug.

## What is in here

| File | What it is |
|---|---|
| `case_creator.xlsx` | The case creator. **No entities sheet** — FormShare writes that itself, which is the whole point |
| `case_follow_up.xlsx` | A follow-up, selecting from `demo_cases.csv` |
| `demo_cases.csv` | A placeholder, so the follow-up's required file is satisfied before FormShare starts generating the real one |
| `register_case.xml` | A registration as a device that made an entity sends one |
| `follow_up.xml` | A follow-up against the case that registration creates |
| `follow_up_unknown_case.xml` | A follow-up against a case that does not exist |

---

## 1. A project that serves its cases as an entity list

New project, code **`demo`**. Tick both:

- **Use a case/longitudinal workflow**
- **Cases work offline** — only shown when the deployment can serve entities, and
  only settable before the project has any form

## 2. An assistant

Add one to the project and give it a password. You need it to submit later.

## 3. The case creator form

Upload `case_creator.xlsx`. FormShare will ask three things about it:

| It asks | Answer |
|---|---|
| Which variable identifies each case | `hid` |
| Which variable labels each case | `fname` |
| Which variable records the date of a case | `coll_date` |

Then give the assistant access to the form, and **create its repository**. Wait
for it to finish — it is a background job.

**Look at what FormShare did.** Download the form back (*Get ODK form*) and open
it: there is now an `entities` sheet you did not write, naming `demo_cases` and
labelling each case with `${fname}`. That is what makes the form mint a case
identity on the device.

## 4. The follow-up form

Upload `case_follow_up.xlsx` as a **Simple follow-up**:

| It asks | Answer |
|---|---|
| Type of case form | Simple follow-up |
| Which variable searches and selects a case | `hid` |
| Which variable records the date of a new data point | `fu_date` |
| Which variable controls duplicate data | `survey_id` |

Give the assistant access, upload `demo_cases.csv` as a form file, and create the
repository.

> **Try getting this wrong.** Edit `case_follow_up.xlsx` so it selects from
> `households.csv` instead and upload that. It is refused, and the message names
> the file it should have used. Without that check the form would simply resolve
> no list at all — an empty select, with nothing reported anywhere.

## 5. Register a case the way a device does

`register_case.xml` is a registration carrying the entity block a form with an
entities sheet produces. The part that matters:

```xml
<entity dataset="demo_cases" create="1" id="044be76f-4a5f-48f6-9d39-ba680862079b">
  <label>Maria Gomez</label>
</entity>
```

That `id` was minted **on the device**, at first load, before anything was sent.
Submit it:

```bash
curl -u <assistant>:<password> --digest \
     -F "xml_submission_file=@register_case.xml" \
     http://<host>/user/<owner>/project/demo/submission
```

## 6. See what the device is sent

Fetch the follow-up form's manifest as the assistant:

```bash
curl -u <assistant>:<password> --digest \
     http://<host>/user/<owner>/project/demo/demo_case_followup/manifest
```

Two things to look for:

```xml
<mediaFile type="entityList">      <!-- an attribute; without it the client -->
  <filename>demo_cases.csv</filename>   <!-- treats this as a plain attachment -->
```

Then download that `<downloadUrl>`. The CSV has `name`, `label` **and
`__version`** — a client that cannot find `__version` discards the whole list
without reporting anything — and the case's `name` is `044be76f-…`, the id the
device minted, **not** `HH-042`. If it were `HH-042` the device would not
recognise the case it registered itself, and would keep two of it.

## 7. Follow it up

`follow_up.xml` carries that same id in `hid`, which is what the device stores
when you pick from an entity list.

```bash
curl -u <assistant>:<password> --digest \
     -F "xml_submission_file=@follow_up.xml" \
     http://<host>/user/<owner>/project/demo/submission
```

Accepted, with no message. It reached the repository because the follow-up
trigger links on `rowuuid`, and `rowuuid` is the id the device minted.

## 8. Follow up a case that does not exist

```bash
curl -u <assistant>:<password> --digest \
     -F "xml_submission_file=@follow_up_unknown_case.xml" \
     http://<host>/user/<owner>/project/demo/submission
```

Still `201` — the submission is not thrown away, it goes to the JSON logs to be
cleaned — but now the reply says so, and ODK Collect shows it to the enumerator:

```xml
<OpenRosaResponse xmlns="http://openrosa.org/http/response">
  <message>This submission could not be stored and has been sent to the logs.
           A colleague will contact you to fix it.</message>
</OpenRosaResponse>
```

## 9. Check the database

```sql
-- the case: rowuuid is the id the DEVICE minted, not one the server made up
SELECT hid, fname, rowuuid, _active FROM <creator_schema>.maintable;

-- the follow-up: hid holds that same uuid
SELECT hid, fu_date, survey_id, score FROM <followup_schema>.maintable;

-- and the trigger that let it in
SELECT ACTION_STATEMENT FROM information_schema.triggers
 WHERE TRIGGER_SCHEMA = '<followup_schema>' AND ACTION_TIMING = 'BEFORE';
```

The trigger reads `WHERE _active = 1 AND rowuuid = new.hid`. Under the old
linkage it compared against the case identifier, and step 7 would have been
refused — a follow-up made offline could never be accepted.

Find the schemas with:

```sql
SELECT form_id, form_schema FROM odkform f JOIN project p USING (project_id)
 WHERE p.project_code = 'demo';
```

---

## Running it twice

`rowuuid` is uniquely indexed, so resubmitting `register_case.xml` collides and
leaves one row rather than registering the case twice — that is the idempotency
the device-minted id buys. To register a *second* case, change both the `id`
attribute and `instanceID` to fresh **version 4** uuids, and change `hid`. A
non-v4 id is replaced by the server, and on the device it would be dropped
outright.

```bash
python3 -c "import uuid; print(uuid.uuid4())"
```

## If something does not work

| Symptom | Likely cause |
|---|---|
| No "Cases work offline" checkbox | `odktools.supports_entities` is not true, or the project already has forms |
| The downloaded creator has no `entities` sheet | The project did not opt in, or the deployment cannot serve entities |
| Follow-up upload refused, naming another file | Project code is not `demo`, so the derived list name does not match the form |
| Repository never finishes | Celery is not running |
| Follow-up rejected in step 7 | The repository was built before the rowuuid linkage; rebuild it |
| Manifest has no `type="entityList"` | The project did not opt in |
