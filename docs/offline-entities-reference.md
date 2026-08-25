# Offline entities in FormShare — reference and open discussion

What was built to let a project serve its cases to ODK as an entity list, why it
is shaped the way it is, and what is still open.

**Audience:** whoever picks entities up next, including a session with no memory
of the work. Read this first; it is meant to replace re-deriving any of it.

**Status.** Implemented on `feature/offline-entities` (`57c9dda5`), which needs
RSTools `main_3.0_entities`. The workflow passes end to end against a real
database — a case registered with a device-minted uuid, followed up, and both
rows verified in MySQL. Sections 1–5 describe what exists. Sections 6–8 are
**discussion**: the three questions that were asked but not answered in code, with
recommendations rather than decisions. Section 9 lists known gaps, two of which
are defects.

Companion documents:

| | |
|---|---|
| `docs/offline-entities-plan.md` | how the work was sequenced, the spikes, the decisions |
| `docs/offline-entities-example/README.md` | walk the workflow by hand |
| `RSTools/docs/odk-offline-entities.md` | the schema-generation side |
| `kotlincollect/docs/ENTITIES.md` | how ODK entities actually work |
| `kotlincollect/docs/FORMSHARE-ENTITY-LIST-SPIKE.md` | the wire contract, answered with tests |

---

## 1. The problem, in one paragraph

FormShare has held longitudinal cases **relationally** since 2021, before ODK
had entities. A case is a row in the case creator form's repository; a follow-up
is a row in its own repository linked to it; a `BEFORE INSERT` trigger refuses a
follow-up whose creator row is not `_active`. What it could not do was **offline**:
the case list reached a device as a server-generated CSV, so a case registered in
the field was invisible to a follow-up form until the device synced. ODK's entity
mechanism solves exactly that, and the client keeps its own store it can add to
while offline.

## 2. The idea that makes it cheap

FormShare already asks, at form upload, which variable identifies a case, which
labels it, and which dates it. Those answers are precisely what an ODK `entities`
sheet needs. So **the user never writes one** — FormShare writes it into the
uploaded workbook before pyxform reads it.

pyxform does more of the work than expected. Verified against the pinned
`pyxform==4.1.0`:

- it emits `entities:entities-version="2024.1.0"` **by default**, which is the
  version a client needs to create entities offline. No upgrade needed.
- an `offline` column in the entities sheet is **rejected** by that version. Do
  not add one.
- it mints the entity id itself:
  `<setvalue ref="/data/meta/entity/@id" event="odk-instance-first-load" value="uuid()"/>`
- for update forms it also generates the `baseVersion`/`trunkVersion`/`branchId`
  calculates that pull from the secondary instance.

So the injected sheet is two rows: `list_name` and `label`.

## 3. The identity problem, which is the whole design

This is the part to understand before changing anything.

An ODK client keys an entity on the CSV's `name` column. A case registered
offline is known on the device by **the uuid the device minted**. FormShare's
follow-up trigger, meanwhile, compared the value a follow-up stored against the
creator's **primary key**.

Those cannot both be `name`, and the failure is not symmetric:

| | `name` = case identifier | `name` = `rowuuid` |
|---|---|---|
| Register online, follow up | accepted | accepted |
| Register **offline**, follow up offline | device stored the uuid → `WHERE hid = '<uuid>'` → **refused** | accepted |
| After sync | server sends `HH-042`; device does not recognise its own case → **two entities** | device matches → one entity |

The offline row is the entire feature, and the left column fails it twice.

There is no way to dodge it by making the device mint the case identifier as the
entity id: pyxform mints it with `uuid()`, and overriding it via `entity_id` in
the entities sheet flips pyxform into *update* mode and fails ODK validation on a
creator form (`Instance referenced by instance(...)/root/item/__trunkVersion does
not exist`) — tested.

**So a follow-up links to its creator on `rowuuid`.** Three values in
`create_repository` now come from one `link_field`: `creator_field`, the `rfield`
of the foreign key on the selector column, and the field whose SQL type the
selector column is cut to. It needed **no RSTools change** —
`createFromXML` interpolates whatever `creator_field` says.

The generated trigger, read back from a live repository:

```sql
FROM FS_c125c233….maintable WHERE _active = 1 AND rowuuid = new.hid
```

No repository migration was needed: no client runs a longitudinal workflow on
RSTools yet. That window is now closed — this is the linkage from here on.

## 4. What was built

### 4.1 `formshare/processes/odk/entities.py`

The whole feature's vocabulary, deliberately small:

| Function | What it decides |
|---|---|
| `deployment_supports_entities(request)` | `odktools.supports_entities` in the ini. ODKTools cannot build an entity form: it would leave a stray `entity` column and mint v1 uuids the client silently drops |
| `project_uses_entities(request, details)` | capability **and** the project opted in |
| `case_list_name(project_code)` | the entity list name, derived so it is knowable before the creator is uploaded (§4.4) |
| `case_list_file_name(project_code)` | that, plus `.csv` |
| `wrong_case_selector_file(...)` | the file a follow-up must select from, or `None` |
| `inject_entity_declaration(xlsx, dataset, label)` | writes the `entities` sheet into the workbook, in place |

### 4.2 Injection, in the upload path

`upload_odk_form` (`processes/odk/api.py:1457`), between the workbook landing on
disk and `xls2xform_convert`. Both pyxform calls read the same file, so the XForm
the device downloads and the schema the repository is built from come from one
edit and cannot disagree.

Gated on all four: `project_case == 1`, `form_casetype == 1` (creator only),
`project_entities == 1`, and the capability flag.

RSTools leaves the declaration out of the schema, so this adds no column and does
not disturb merging against a version that predates it — verified by running the
real `jxformtomysql` over an injected form and diffing the columns.

### 4.3 The submission side

`set_rowuuid_from_entity` in `store_json_file`, beside `_project_code` and
`_active`. It copies the device-minted entity id onto `rowuuid`, which
`JSONToMySQL` adopts on the main table when the value is v4.

**The JSON key is `meta/entity/@id`, not `__id`.** Verified by running the built
`XMLtoJSON`: an attribute is keyed by its node's path, an `@`, and its name.
`__id` is what the *entity model* calls it — it surfaces as `name` in the CSV and
in form expressions, and never appears in a submission.

It adopts **only on create**, and it decides that from the submission itself
(`@create` truthy, `@update` not). On an update form the same attribute names *the
case being updated* — a row that already exists and whose rowuuid it already is —
so adopting it there would make the follow-up claim the creator's identity and the
insert would be refused. `create` + `update` together is an upsert, which is
ambiguous, so it is left alone. This is why `JSONToMySQL` deliberately does not
read the attribute itself: from inside it, create and update are indistinguishable.

### 4.4 Naming, and why it is derived

The client names an entity list after the media file minus its extension, and
that name has to equal the creator's `<entity dataset>` **and** the follow-up's
`select_one_from_file <name>.csv`.

The awkwardness: the creator is uploaded first, but the file name a client asks
for comes from a *follow-up*, which does not exist yet — and FormShare stores it
per follow-up form in `Odkform.form_caseselectorfilename`, read from whatever the
user wrote. Historically FormShare **adapted** to the user's file name. For
entities that has to invert.

Deriving the name from the project code is what lets both sides agree without
anyone choosing twice. `demo` → `demo_cases` → `demo_cases.csv`. It is sanitised
to a valid XML identifier, file name and secondary-instance id all at once.

A follow-up pointing elsewhere is **refused at upload**, naming the file it
should have used. Without that check the form resolves no list at all and the
select is simply empty — no error, on the server or the device.

### 4.5 The manifest and the CSV

`generate_manifest` could only write child elements. `type` is an **attribute**,
and it is how a client tells an entity list from an attachment
(`isEntityList = type != null`), so it is now special-cased. Everything else stays
a child, so `<integrityUrl>` and the rest are unaffected.

`generate_lookup_file` gained an `as_entity_list` branch: `name` becomes
`rowuuid`, the nominated case identifier goes out as its own column, and
`__version` is added as a constant `1`.

`__version` is not optional. A client that cannot find that column **discards the
whole list without reporting anything**, and a value that is not an integer
raises. Both failures are invisible from the server.

The non-entity output is byte-identical to before.

### 4.6 Opting in

`project_entities` on the project (alembic `a3e17c94b210`), a checkbox shown only
where the deployment can serve entities, forced to 0 without the case switch, and
**settable before the first form and never after** — turning it on later would
advertise a list the already-built creator cannot populate; turning it off later
would strand follow-up repositories linked on rowuuid. `EditProjectView` drops the
key once `total_forms > 0`, which leaves the stored value alone.

### 4.7 Telling the enumerator

Unrelated to entities but found along the way, and it matters more once cases are
followed up offline.

A trigger rejection is JSONToMySQL exit code 2 — *"an SQL error that goes to the
logs"*. FormShare quarantines the submission via `add_json_log` and returns
**201**. That is deliberate and right: the data is not lost, the enumerator is not
blocked, and someone reconciles centrally. But the reply was a bare status with no
body, so the enumerator saw plain success and walked away.

Submissions now carry an `<OpenRosaResponse><message>`, which ODK Collect
displays. Status codes are unchanged, so Collect still clears its outbox.

*(An earlier draft of the plan claimed rejections came back as 5xx and were
retried forever. That was wrong; the behaviour above is what the code does.)*

## 5. Tests

| | |
|---|---|
| `formshare/tests/test_01_entities.py` | 26 tests, no app, no database, ~0.2s. Naming the file explicitly makes pytest ignore `testpaths`, so the gate does not run |
| `formshare/tests/steps/entities.py` | the whole workflow, ~94s, under `FORMSHARE_TEST_ENTITIES=true` |

```bash
export FORMSHARE_PYTEST_RUNNING=true
pytest formshare/tests/test_01_entities.py -v          # fast
FORMSHARE_TEST_ENTITIES=true pytest formshare/tests/test_00_root.py  # the workflow
```

The workflow test builds its forms and submissions in code rather than keeping
fixtures, because the list name is derived from the project code — a fixture with
`entity001_cases.csv` baked in would stop testing the contract the moment that
derivation changed.

What it proves, confirmed against MySQL afterwards:

```
creator:   hid=HH-042  rowuuid=645b4bd4-bef7-439e-b776-79a31886b8f5  _active=1
follow-up: hid=645b4bd4-bef7-439e-b776-79a31886b8f5  score=7
trigger:   WHERE _active = 1 AND rowuuid = new.hid
```

That single follow-up row is the thesis: an identity minted on the device
survives into `rowuuid`, and a follow-up carrying it is accepted. Plus the
negatives — a follow-up against a case that does not exist is quarantined *with a
message*, `entity002` (entities without case) has `entities = 0`, and a follow-up
selecting from the wrong file is refused at upload.

**Note on the gate.** `FORMSHARE_TEST_ENTITIES=true` currently does two things:
it enables the entity step *and* skips most of the suite, which is what makes the
workflow runnable in 94 seconds instead of 90 minutes. Those two effects should
be separated before merging, so the entity step can also run inside a full gate.

---

# Discussion

Three questions were asked and are not settled in code. What follows is
reasoning and a recommendation for each, not a decision.

## 6. An expert ODK user uploads a form that already has an `entities` sheet

`inject_entity_declaration` finds the sheet and leaves it alone, on the reasoning
that the user meant it and a second declaration would collide. That is right in
some cases and **wrong in one**, and it is worth being precise about which.

### 6.1 Non-case project, or entities not enabled

Injection is never attempted, so the sheet passes straight through. pyxform emits
a 2024.1.0 form with their `<entity>` block. Two consequences:

- On **RSTools** the declaration is skipped and the schema is clean. On
  **ODKTools** it becomes a stray `entity text` column — silently, since
  JXFormToMysql reports `Done without errors`. That is the pre-existing defect
  RSTools fixed; a deployment on ODKTools still has it, and nothing warns.
- **`set_rowuuid_from_entity` still fires.** It is called unconditionally in
  `store_json_file` and gates only on the submission's own keys, so a
  hand-authored entities form gets its `rowuuid` replaced by the device-minted id
  **regardless of the capability flag or the project's opt-in.**

  Is that harmful? Not obviously: the DB trigger still validates v4, the unique
  index still prevents collisions, and nothing links on rowuuid in a non-entity
  project. It even buys idempotent resubmission. But it is the one piece of this
  feature that is not behind the two gates, and that inconsistency will surprise
  someone. **Recommendation:** leave the behaviour, document it here, and if it is
  ever tightened, tighten it deliberately rather than by accident.

### 6.2 Entity-enabled case project, expert's sheet on the **creator** — a defect

This is the case that breaks, quietly.

FormShare keeps their `list_name` — say `households`. But it serves the case list
as `demo_cases.csv` with `type="entityList"`, so the **device names the list
`demo_cases`**. The creator then creates entities in a list called `households`,
which the device has never heard of, while follow-ups read `demo_cases`.

A case registered offline lands in the wrong list and the follow-up form never
sees it. Nothing errors. It is exactly the failure the follow-up file-name check
exists to prevent, on the creator side where there is no check.

**Recommendation: refuse it.** If the project serves entities and the uploaded
creator already declares an `entities` sheet whose `list_name` is not
`case_list_name(project_code)`, reject the upload and say which name is required
— the same shape as `wrong_case_selector_file`. Rewriting their sheet silently is
worse: it would discard `save_to` mappings they wrote deliberately.

A sheet that *does* already name the right list should pass, which is also what
makes re-uploading a downloaded workbook idempotent — worth keeping, because the
stored copy is the injected one.

### 6.3 Entity-enabled project, expert's sheet on a **follow-up**

Injection never touches follow-ups, so their sheet passes through and the form
can create or update entities. The file-name check still applies, so it cannot
point at the wrong list.

If they wrote `create="1"` on a follow-up, `set_rowuuid_from_entity` adopts the
id as that follow-up row's rowuuid. Each finalize mints a fresh uuid, so nothing
collides. Unmanaged but harmless.

If they wrote `update="1"`, see §7 — the server does nothing with it today, so the
update is silently a no-op as far as FormShare's data is concerned.

## 7. A follow-up that creates or updates an entity property

The honest summary: **FormShare can already do what users want here, and it is not
ODK entity update.**

### 7.1 What ODK entity update would actually require

1. **Injection for follow-ups** — an `entities` sheet with `entity_id =
   ${form_caseselector}` and `update_if`, plus `save_to` on the fields to write.
   pyxform then generates the `baseVersion`/`trunkVersion`/`branchId` calculates
   itself, so that part is free.
2. **`__version` has to become real state.** It is a constant `1` today. The
   client's merge compares versions three ways (server ahead, same version, local
   ahead); against a constant, a locally-updated entity always looks *local ahead*
   and never reconciles. So the creator repository needs an integer version
   incremented on every property change.
3. **The updated property has to land somewhere.** An ODK property belongs to the
   entity; FormShare's case is a row in the *creator's* repository. So a follow-up
   updating `score` has to write into the creator's row — which today follow-ups
   never do; they only insert into their own table.
4. **Conflict handling.** Two devices updating one case offline. Central does
   last-write-wins plus a flag for review, and KotlinCollect has **no conflict
   UI** (ENTITIES.md §8). FormShare has no equivalent at all.
5. `set_rowuuid_from_entity` must keep refusing updates — already the case.

Item 4 is the one to weigh. Adopting entity update means adopting ODK's
*reconcile-after-the-fact* model into a system whose whole argument is that
integrity is enforced by the database before the write. That is a real
philosophical cost, not just work.

### 7.2 What to do instead

**Propagate with triggers, and let the entity list follow.** FormShare already
has the mechanism: a MySQL trigger on the follow-up table that writes values back
into the creator row. That is what the `formshare_triggers` skill exists for —
summing disbursements back onto a case, and so on. The case row changes, the next
generated entity list carries the new value as a property, and the device picks it
up on sync. Users get "the follow-up changed the case" without FormShare adopting
offline reconciliation.

The cost is that the change is **server-side only**: a device that registered a
case offline will not see the updated property until it syncs. For most
longitudinal work that is fine, and it is honest — the value was computed from
data the server has and the device does not.

### 7.3 The narrow piece that *is* worth building

**`_active` as an entity property.**

Today the activate/deactivate case types are served by filtering server-side:
`generate_lookup_file(..., only_inactive)` emits `WHERE _active = 0` or `= 1`.
Offline that cannot work — the device has one list.

As a property, the filter moves into the form as an itemset predicate
(`[active='1']`), which KotlinCollect pushes down to SQL and is proven at 1000
entities. Deactivate/activate follow-ups then work offline, and the whole thing
stays create-only: no `__version` reconciliation, no writing to the creator row
from a follow-up, no conflict model.

That is the highest value per unit of risk in this whole area. It would be my
next piece of work.

## 8. What else entities need

Roughly in the order I would do them.

### 8.1 Encryption × entities — test this before trusting anything

ENTITIES.md §8 flags it as unverified, and FormShare has project encryption
(`project_encrypted`). The `<entity>` block rides **inside** the instance XML. If
the instance is encrypted, `XMLtoJSON` may never see `meta/entity/@id`, and
`set_rowuuid_from_entity` becomes a silent no-op — the case gets a server-minted
rowuuid, the device keeps its own, and every offline follow-up is refused.

This is the highest-risk unknown in the feature and it is cheap to check: enable
encryption on a case project and run the workflow example. **Do this first.**

### 8.2 The form-update path does not inject — a defect

Injection is in `upload_odk_form` only. `update_odk_form` has the selector-file
check but **no injection**, so publishing a new version of a creator form from a
fresh workbook produces a form with no `entities` sheet: it stops minting entity
ids, and cases registered on that version are invisible to the entity list.

It is masked in the common path — a user who downloads the stored workbook and
edits it gets the injected sheet along with it, and injection is idempotent. But a
user who uploads a freshly exported workbook silently loses it.

**Fix:** call the same injection from `update_odk_form`, gated identically.

### 8.3 Deletion sync (`<integrityUrl>`)

A case deleted server-side stays on the device forever. `<integrityUrl>` is a
child element, so it is a one-key addition to the manifest; it needs an endpoint
reporting which of a list of ids were deleted, with Central's **single
comma-joined `?id=a,b,c`** encoding (repeated `?id=&id=` yields a 500 there, and
KotlinCollect only sends the joined form).

FormShare deletes are soft-ish already (`_active`), so decide what "deleted" means
on the wire: gone from the repository, or inactive.

### 8.4 The case-fields UI now half-lies

`CaseLookUp.field_as = "name"` still lets the project owner choose which variable
surfaces as `name`. For an entity project that choice is **ignored** — `name` is
`rowuuid`, and their field goes out as an ordinary column. The UI should say so,
or hide the choice.

### 8.5 Barcode selectors

With rowuuid linking, a scanned code has to carry the rowuuid, so a barcode
printed with the case identifier will not match. The creator form *can* surface
the uuid — the device mints it at first load, so it is available in the same
session the case is registered — but nothing does that today, and it is untested.

### 8.6 Stock ODK Collect

Still open. S3 lowered the stakes considerably: the wire contract it produced is
*"100% OpenRosa-manifest-driven and server-agnostic"* on both platforms, with no
Central-specific assumption on the import path. Building to it is close to
supporting stock Collect already. It has simply never been run.

### 8.7 Approval lists

`type="approvalEntityList"` sets `needsApproval`, which **blocks local offline
create** into that list. FormShare has no notion of approval. Only relevant if
cases should require review before enumerators can follow them up — a plausible
feature, entirely unbuilt.

### 8.8 Multi-entity submissions (2025.1)

Entities declared inside groups and repeats, so one submission creates several.
FormShare's model is one case per creator submission; there is no obvious mapping,
and no demand yet. Note it and move on.

### 8.9 `generated_case.csv` in the gate

That fixture asserts the non-entity CSV, which is unchanged — but if the entity
variant ever becomes the default, it changes. Do not let it be updated
reflexively; the diff is the signal.

---

## 9. Known gaps, collected

| | Where | Severity |
|---|---|---|
| Encryption may break the rowuuid mapping silently | §8.1 | **unknown, test first** |
| `update_odk_form` does not inject | §8.2 | **defect** |
| An expert's `entities` sheet with a mismatched `list_name` is accepted | §6.2 | **defect** |
| `set_rowuuid_from_entity` is not behind the capability gate | §6.1 | inconsistency |
| No deletion sync | §8.3 | missing feature |
| Case-fields UI ignores the `name` choice for entity projects | §8.4 | confusing |
| Barcode selectors need the rowuuid in the code | §8.5 | untested |
| `FORMSHARE_TEST_ENTITIES` both enables entities and skips the gate | §5 | tidy before merge |
| `test_config.json` is gitignored, so the two settings tests need are local only | — | onboarding trap |

## 10. If you change one thing, know this

The CSV's `name` column and the follow-up trigger's `creator_field` **must move
together**. Sending `rowuuid` as `name` while the trigger compares the case
identifier refuses *every* follow-up, online and offline. Sending the case
identifier while the trigger compares `rowuuid` does the same. They are set in
two different files —
`processes/db/form.py:generate_lookup_file` and
`processes/odk/api.py:create_repository` — and nothing enforces the pairing.
The workflow test is what catches it; its assertion says so in as many words.
