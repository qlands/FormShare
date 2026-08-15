# Offline entities — implementation and QA plan

How FormShare might let an enumerator register a case **offline** and immediately
run a follow-up form against it on the same device, by emitting its case list as
an ODK entity list.

**Audience:** whoever picks up a stage. Three repositories are involved and each
has its own session; this is the shared reference they coordinate against.

**Status, 2026-08-15.** All three Phase 0 spikes are done and Phases 1, 2, 3 and
5 are implemented — RSTools on `main_3.0_entities`, FormShare on
`feature/offline-entities`. The XLSX injection is verified end to end: an
injected workbook converts to an `entities-version="2024.1.0"` XForm and still
produces a schema with no stray `entity` column.

Implementing Phase 4 surfaced a conflict between what an ODK client needs the
case list's `name` column to be and what the follow-up trigger needs it to be.
It is **resolved** (§1.2): a follow-up now links to its creator on `rowuuid`,
which turned out to need no RSTools change. No client runs a longitudinal
workflow on RSTools yet, so there is nothing to migrate.

**What is left before it can be switched on:** nothing has been run against a
live server or a device, and there are no tests. Every piece is written.

A follow-up form is checked at upload, and at update, against the project's
case-list file name (`wrong_case_selector_file`). A mismatch is refused with the
name the form should have used — otherwise the form resolves no list at all and
the select is simply empty, with nothing reported. A barcode selector is left
alone: it carries the case id itself rather than picking from a list, and what
that code has to contain is the rowuuid, which cannot be checked at upload.

The project opt-in is a checkbox on the project form, shown only where the
deployment supports entities, meaningless without the case switch above it, and
**settled before the first form and never after** — turning it on later would
advertise a case list as an entity list that the already built creator form
cannot populate, and turning it off later would leave follow-up repositories
linked on rowuuid while the list stopped sending it. `EditProjectView` drops the
key once `total_forms > 0`, which leaves the stored value untouched.

Two decisions remain open (§4): stock Collect or not, and create-only or update.

---

## 0. The problem

FormShare has supported longitudinal studies relationally since 2021, predating
ODK entities. A case is a row in the case-creator form's repository, follow-ups
link to it, and a `BEFORE INSERT` trigger rejects a follow-up whose creator row
is not `_active`.

The gap is offline. The case list reaches the device as a server-generated CSV
(`generate_lookup_file`, `processes/db/form.py:220`), so a case registered
offline is invisible to a follow-up form until the device syncs.

The proposal: derive ODK entity declarations from answers FormShare **already
collects** at form upload — `form_pkey`, `form_caselabel`, `form_casedatetime`,
`form_caseselector`, `form_casetype`, plus the `CaseLookUp` table — inject them
into the uploaded XLSX, and let the client's existing offline entity machinery do
the rest. The user never writes an `entities` sheet.

### The three repositories

| Repo | Role | Its doc |
|---|---|---|
| **FormShare** | XLSX injection, manifest, lookup CSV, submission responses | this file |
| **RSTools** | schema generation, submission insert, triggers | `RSTools/docs/odk-offline-entities.md` |
| **KotlinCollect** | the client; already implements entities | `kotlincollect/docs/ENTITIES.md`, `FORMSHARE-ENTITY-LIST-SPIKE.md` |

### The constraint that shapes sequencing

**RSTools is not in CI, and CI cannot test this feature at all.**

FormShare's CircleCI runs against **ODKTools** — a light build that does *not*
support entities. RSTools-dependent tests are gated behind
`os.environ.get("USE_RSTOOLS", "false")` (`formshare/tests/test_00_root.py:52`,
`:57`, `:73`; `steps/forms.py:154`, `:185`, `:447`) and **run locally only**.

Two consequences:

1. **Every layer of the QA strategy that touches entities is local-only.** CI
   will keep proving that nothing regressed for ODKTools deployments, which is
   worth having, but it will never exercise the feature. Plan for a documented
   local run as the real gate.
2. **Entity support must be gated at runtime**, because the same FormShare code
   runs against both toolchains. Injecting an `entities` sheet when the installed
   toolchain is ODKTools would produce a junk `entity` column and a case list the
   device silently refuses to import. See §7.

---

## 1. Phase 0 — spikes

### S1 — pyxform capability ✅ done, 2026-08-15

*Does `pyxform==4.1.0`, the pinned version, emit what we need?* Tested in an
isolated venv against the two calls FormShare makes at
`processes/odk/api.py:1433` and `:1436`.

**Yes, and it does more of the work than expected.**

- `entities:entities-version="2024.1.0"` is emitted **by default**, with no
  XLSForm opt-in. 2024.1 is exactly what the client needs to produce local
  entities offline. **No pyxform upgrade is required.**
- An `offline` column in the `entities` sheet is **rejected** by 4.1.0 — do not
  inject one.
- Both a **create** form (`list_name` + `label`) and an **update** form
  (`list_name` + `entity_id` + `update_if`) convert cleanly.
- pyxform mints the entity id itself:
  `<setvalue ref="/data/meta/entity/@id" event="odk-instance-first-load" value="uuid()"/>`
- For update forms it also generates the `baseVersion`/`trunkVersion`/`branchId`
  calculates that pull from the secondary instance. **FormShare does not have to
  hand-write any of that.**

So the injection is small: an `entities` sheet, plus a `save_to` column on the
survey sheet populated from `CaseLookUp` rows where `field_editable = 1`.

**One problem S1 surfaced.** The entity id lands at `/data/meta/entity/@id` — an
XML *attribute*, not a survey field — so it will **not** become a repository
column on its own. Redirecting it to a field we control does not work: setting
`entity_id` on a creator form makes pyxform treat it as an update form and
generate a `trunkVersion` calculate against a secondary instance the creator form
does not have, which fails ODK validation. Resolving this is an RSTools question
(does `XMLtoJSON` surface that attribute?) and is written up in their §1.

### S2 — JXFormToMysql tolerance ✅ done, 2026-08-15

*Does the schema generator survive an entities `.srv`?* Ran the real binary
against the S1 output.

**It runs, reports `Done without errors`, and silently emits a junk column:**

```sql
hh_head text COMMENT "Head",
entity text COMMENT "Without label",     -- the entity declaration, as a column
```

pyxform puts the entity declaration **inside the `meta` group** as a node of
type `entity` (the earlier assumption that it sat outside `children` was wrong).
JXFormToMysql treats the unknown type as an ordinary field and names a `text`
column after it.

Full reproduction, the fixtures, and the ask are in
`RSTools/docs/odk-offline-entities.md` §3. Fixtures are committed at
`RSTools/tests/entities_spike/`.

### S3 — KotlinCollect wire contract ✅ done, 2026-08-15

Answered in `kotlincollect/docs/FORMSHARE-ENTITY-LIST-SPIKE.md` §8-11, every
answer traced to a file:line and backed by `IosFormShareEntityImportTest` (5/5,
MockEngine). One contract serves Android and iOS.

The headlines:

- **Q6: there is no v4-UUID check on import.** `id` is the `name` column
  verbatim. The v4 check applies only on *finalize*. So import alone needs no
  UUID minting — but see §2.1 below, because the **round trip** does.
- **Q1:** `type` is an attribute, and import triggers on *any* non-null value.
  It must be `entityList`, **not** `approvalEntityList` — the latter sets
  `needsApproval`, which blocks local offline create.
- **Q3:** `name`, `label`, `__version` are all required. A missing column aborts
  the whole list import **silently**. An empty or non-integer `__version`
  **throws**. It does not default to 0.
- **Q4:** unknown columns become entity properties, so today's leading
  `list_name` column is harmless.
- **Q5:** the list is named from the manifest `<filename>` minus `.csv`, and
  must match the follow-up's `select_one_from_file <name>.csv` and the creator's
  `<entity dataset>`.
- **Q7:** the `md5:` prefix is tolerated, but the `<hash>` string must be
  *consistent* between fetches — the import gate compares it verbatim.

### 1.1 What the two spikes together revealed

Neither session could see this alone: S3 scoped out the create side, and RSTools
never sees the CSV.

**The round trip duplicates every offline-created case.**

1. Device registers offline → local entity id = a v4 UUID, `state = OFFLINE`
2. Submission syncs → FormShare stores the row
3. FormShare regenerates the CSV → `name` = the household code, from
   `CaseLookUp.field_as = "name"`
4. Device imports → that id is not present locally → **inserts a second entity**
5. The original is absent from the server CSV but is `OFFLINE`, and ENTITIES.md
   §5.3 never deletes those — so it stays

One case, two entities, permanently.

The obvious fix — make the CSV's `name` the `rowuuid` — **cannot be applied on
its own, and trying it breaks follow-ups outright.** This was found while
implementing it, and it is now the one thing blocking the feature.

### 1.2 The identity fork — resolved by linking on rowuuid

**Decided 2026-08-15: a follow-up links to its creator on `rowuuid`.** No client
runs a longitudinal workflow on RSTools yet, so there is nothing to migrate and
no reason to carry the old linkage forward into the entity path.

It turned out to need **no RSTools change**. `createFromXML` interpolates
whatever `creator_field` says (`main.cpp:571`, `:573`, `:583`); FormShare writes
that attribute. So it is three values in `create_repository`
(`processes/odk/api.py`): `creator_field`, the `rfield` of the foreign key on
the selector column, and the field whose type the selector column is cut to.
All now come from one `link_field`, which is `rowuuid` for a project serving
entities and the nominated case identifier otherwise.

It is also the better relational choice on its own terms — child rows linked on
an immutable uuid rather than on a meaningful key someone picked, which means
the case identifier could become editable later without orphaning follow-ups.

**Known limitation: barcode selectors.** A follow-up may select a case by
scanning a barcode instead of picking from the list. With rowuuid linking, the
scanned value has to be the rowuuid, so a barcode printed with the case
identifier will not match. Untested, and out of scope until someone needs it.

The rest of this section is why it had to be decided at all.

#### The conflict

Two requirements want `name` to be two different things.

| Wants `name` to be | Why |
|---|---|
| the **case identifier** (`form_pkey`) | A follow-up stores whatever the select returns, and the `case_followup` trigger compares that value against the creator's primary key — `creator_field`, set from `form_pkey` at `processes/odk/api.py:3271`. A follow-up carrying anything else is refused with *"Case ID: X is inactive or does not exist."* |
| the **entity id** (`rowuuid`) | An ODK client keys an entity on `name`. A case registered offline is known on the device by the v4 uuid the device minted. If the row comes back under a different name the device treats it as a new case and keeps both — §1.1. |

They cannot both hold, and the two have to move together: sending `rowuuid` as
`name` while the trigger still compares the case identifier refuses **every**
follow-up, online and offline, not just the offline ones.

Worked example — project `DEMO-01`, creator keyed on `hh_code`, follow-up
selecting from `demo_01_cases.csv`:

| | `name` = `hh_code`, link on `hh_code` | `name` = `rowuuid`, link on `rowuuid` |
|---|---|---|
| Register **online**, follow up | select stores `HH-042` → `WHERE hh_code='HH-042'` → 1 row → accepted | select stores `d4a4…` → `WHERE rowuuid='d4a4…'` → 1 row → accepted |
| Register **offline**, follow up offline | device minted `d4a4…`, so select stores `d4a4…` → `WHERE hh_code='d4a4…'` → **0 rows → refused** | select stores `d4a4…` → `WHERE rowuuid='d4a4…'` → 1 row → accepted |
| After sync | server sends `HH-042`; device does not recognise its own case → **two entities** | server sends `d4a4…`; device matches → `state = ONLINE`, **one entity** |

The offline row is the whole feature, and the left column fails it twice over.

There is no way to dodge it by making the device mint the case identifier as the
entity id: pyxform mints it with `uuid()` in a `setvalue`, and overriding it via
`entity_id` in the entities sheet flips pyxform into update mode and fails ODK
validation on a creator form (`Instance referenced by
instance(households)/root/item/__trunkVersion does not exist`) — tested.

S3's §10 row 4 ("`name` may stay the household code — no change") is right for
import in isolation, which was its scope. The conflict only appears when the
create side and the relational trigger are both in view.

---

## 2. Phase 1 — RSTools foundation ✅ done

Implemented on branch **`main_3.0_entities`**, covered by `tests/test_entities.py`
(96 passing against MySQL 8.4.7). Written up in their §6.

| Work | Outcome |
|---|---|
| Skip the entity declaration | Done — `parseJSONObject` returns on `type: "entity"`; no `entity` column in either fixture |
| Warn on unknown nodes | Done, but keyed on **a container absorbed as a field**, not on an unknown *type* — 81 known types default to `text(255)` and that is correct for `barcode`, `rank`, `hidden`, so a type-keyed warning would fire on ordinary forms |
| Pin the UUID regex to v4 | Done, anchored with `\z`, moved to `common/rowuuidtrigger.h` (there were four copies) |
| Surface XML attributes | Done — `XMLtoJSON` emits `meta/entity/@id` etc.; the bug was general, *any* attribute in *any* form was being dropped |
| Adopt an incoming `rowuuid` | Done, but **only an explicit `rowuuid` key** — see below |

### 2.1 Two decisions that change FormShare's work

**`JSONToMySQL` deliberately does not read `meta/entity/@id`.** On a create form
that attribute is the identity of the row being written; on an **update** form the
same attribute names *the case being updated*, whose rowuuid it already is.
Adopting it there would make the follow-up row claim the creator's identity and
collide on the unique index. From inside `JSONToMySQL` the two are
indistinguishable — it sees a manifest and a flat JSON object.

**So the mapping is FormShare's, per form.** We already gate on
`form_casetype == 1`, which is exactly the fact `JSONToMySQL` lacks. Their
suggested route — inject a `rowuuid` key into the submission JSON, which
`XMLtoJSON` already merges from stdin (`XMLtoJSON/main.cpp:373-383`) — fits
`IXMLSubmission.before_processing_submission`.

**Migration.** The v4 trigger is DDL, so **existing repositories keep the old
trigger and go on minting v1** until rebuilt. A live repository that is to serve
entities needs its rowuuid triggers replaced, and RSTools has no migration for
that. Reinforces §6's opt-in, new-projects-only recommendation.

### 2.2 What RSTools was waiting to hear — answered

1. **How FormShare sets `rowuuid`: it edits the JSON.** After `XMLtoJSON` and
   before `JSONToMySQL`, in the controlling-fields block of `store_json_file`,
   the same place `_project_code` and `_active` are set. Implemented — see §5.
2. **Entity-property columns in `create.xml`: not for now.** Nothing consumes it
   yet, and it stays one `setAttribute` whenever something does.
3. **New repositories only.** No migration of live repositories to the v4
   trigger. Existing case projects keep the old trigger and stay on the
   relational-only path, which is what the opt-in rollout assumes anyway.

**Tests:** `tests/test_entities.py` on `main_3.0_entities`, in the existing
harness (real MySQL, skips without one).

## 3. Phase 2 — FormShare submission feedback ✅ implemented

**An earlier draft of this plan had the premise wrong.** It claimed a trigger
rejection surfaced as a 5xx and was retried forever. It is not. The real
behaviour, traced through the code, is deliberate:

| JSONToMySQL exit | FormShare | Device sees |
|---|---|---|
| `0` — stored | `res_code 0` | 201 |
| **`2` — SQL error, incl. a trigger rejection** | quarantined via `add_json_log(..., 1, ...)` | **201** |
| other | `res_code 1` | 500 |

A rejected follow-up is **accepted and quarantined in the JSON logs for
cleaning**, not lost and not retried. That is the right call — it keeps the
enumerator working and the data recoverable centrally.

The gap was that nobody told the enumerator. `store_submission` computed a
`message` and discarded it at the return, and `views/odk.py` replied with a bare
status and no body.

**What was changed:**

- `store_json_file` (`processes/odk/api.py`) returns a translatable message on
  exit code 2: *"This submission could not be stored and has been sent to the
  logs. A colleague will contact you to fix it."*
- `store_submission` and `store_json_submission` now return
  `(stored, status, message)` instead of `(stored, status)`. All 23 returns in
  the two functions updated.
- `views/odk.py` gained `submission_response(status, message="")`, which emits
  an `<OpenRosaResponse><message>` body with the `X-OpenRosa-Version` headers
  when there is something to say, and the bare status otherwise. All six call
  sites use it.

Status codes are **unchanged** — a quarantined submission still returns 201, so
Collect still clears it from the outbox. The only difference is that the
enumerator now reads why.

Blast radius is contained: the two functions are called from `views/odk.py`
only. Plugins that appear to call `store_submission` (`formatlas`,
`SubmissionProcessing`) import **their own** forks, not FormShare's — verified.

**Still to do:** extend `formshare/tests/steps/case_management.py` — deactivate a
case, submit a follow-up, assert 201 *and* the message body. Needs
`USE_RSTOOLS=true` and a local RSTools build, so it cannot run in CI.

## 4. ◆ Decisions

**D1 — Stock ODK Collect, or KotlinCollect only?** Still open. S3 lowered the
stakes considerably: the wire contract it produced is *"100% OpenRosa-manifest-
driven and server-agnostic"*, with no Central-specific assumption on the import
path. Building to that contract is close to building for stock Collect anyway.

**D2 — Create-only, or entity update as well?** Still open, and RSTools §6.6
sharpened it: **create-only needs nothing further from RSTools** than what is on
`main_3.0_entities`. Update needs FormShare to decide, per submission, that the
entity id names an existing row and must *not* become the new row's identity.

**D3 — core behind a flag, or a plugin? ✅ decided: a flag.** Build in core behind
the capability setting; extract to a plugin later if it earns it. See §7.

`__version` is required either way (S3 Q3), so it is no longer a D1 discriminator.
A case row has `_lastupdate` but no integer version counter, so it is new state
regardless. For a create-only, static case list, a constant `1` satisfies the
client — but it must always be a valid integer, because empty or non-integer
throws and a missing column aborts the import silently.

## 5. Phases 3-6 — gated

3. **XLSX injection** (FormShare) — rewrite the workbook between
   `api.py:1416` and `:1433`, so one injection feeds both the device-facing
   XForm and the MySQL schema and they cannot drift. `openpyxl==3.1.5` is
   already a dependency. Gate on `project_case == 1` **and** on entity capability
   (§7).
4. **Manifest and lookup CSV** (FormShare) — three blocking changes:
   `generate_manifest()` signature change for the `type` attribute; a
   `__version` integer column; and **`name` = `rowuuid`** (§1.1). `<integrityUrl>`
   is optional and only enables the deletion sync.
5. **Submission-side rowuuid mapping** (FormShare) — ✅ **implemented**, see below.
6. **End-to-end** on device, locally, with `USE_RSTOOLS=true`.

### 5.1 The rowuuid mapping, as built

`set_rowuuid_from_entity()` in `processes/odk/api.py`, called from the
controlling-fields block of `store_json_file` beside `_project_code` and
`_active`. It copies the device-minted entity id onto `rowuuid`, which
`JSONToMySQL` adopts on the main table when the value is a v4 UUID.

**The JSON key is `meta/entity/@id`, not `__id`.** Verified by running the built
`XMLtoJSON` from `main_3.0_entities` over a creator submission:

```json
{ "_xform_id_string": "c_s1_d",
  "hh_code": "HH-001",
  "hh_head": "Maria Gomez",
  "meta/entity/@dataset": "households",
  "meta/entity/@id": "d4a4d3f6-1234-4abc-8def-0123456789ab",
  "meta/entity/@create": "1",
  "meta/entity/label": "Maria Gomez",
  "meta/instanceID": "uuid:11111111-2222-4333-8444-555555555555" }
```

`__id` is the name the *entity model* uses (ENTITIES.md §1.1), surfacing as
`name` in the list CSV and in form expressions. It never appears as a submission
JSON key, so keying on it would silently never fire.

**It discriminates create from update using the submission itself** — adopt when
`meta/entity/@create` is truthy and `meta/entity/@update` is not. That is the
distinction RSTools §6.6 says FormShare must make, and reading it from the
`<entity>` block needs no DB lookup and no `form_casetype` check, so it also
works for a hand-authored entities form. `create` + `update` together is an
upsert, which is ambiguous, so it is left alone.

A submission carrying no entity is untouched, which is every submission until a
form declares one — so the mapping is inert until injection (Phase 3) lands.

## 7. Gating: capability and opt-in are two different questions

The same FormShare code runs against RSTools (entities) and ODKTools (no
entities), so entity behaviour must be gated at runtime. Two gates, deliberately
separate:

**Capability — is entity support available in this deployment?** Deployment
configuration. Recommend an **ini setting beside the existing `odktools.path`**,
e.g. `odktools.supports_entities`. Do *not* reuse `USE_RSTOOLS`: it appears only
in `formshare/tests/` and is a test convention; promoting it would make it the
first env var to decide runtime behaviour.

**Opt-in — does this project use entities?** Per-project DB state, chosen by the
user, defaulting off. Existing case projects must keep working untouched, since
switching `name` to `rowuuid` changes what every existing follow-up form stores
as its selector, and their repositories still carry the v1 trigger (§2.1).

### Core behind the flag, or a plugin?

Of the four touchpoints, only one has a usable hook today:

| Touchpoint | Existing hook |
|---|---|
| rowuuid mapping | ✅ `IXMLSubmission.before_processing_submission` |
| XLSX injection | ❌ `IForm.after_odk_form_checks` fires *after* conversion |
| manifest `type` attribute | ❌ `generate_manifest()` is a plain function |
| CSV `__version` / `name` | ❌ `generate_lookup_file()` is a plain function |

So a plugin means designing three new interfaces before the feature's shape is
known — committing to an extension API against something unimplemented.

**Recommendation: build in core behind the capability flag, extract later if it
earns it.** Once it works, the seams are observable rather than guessed, and
extraction is mechanical.

**The condition that flips this:** if entity support is meant to be a
customer-visible tier — SaaS on ODKTools, self-hosted on RSTools, or sold
separately — then it is plugin-shaped and should be built that way from the
start, because retrofitting that boundary is worse than guessing at it.

---

## 6. QA strategy

Four layers, all on infrastructure that already exists.

| Layer | Where | Runs in CI? | Covers |
|---|---|---|---|
| RSTools harness | `RSTools/tests/test_entities.py`, real MySQL | no | rowuuid adoption, v4 rejection, unique-index collision, no junk `entity` column |
| FormShare pytest | `formshare/tests/steps/case_management.py` (2113 lines) | **only with `USE_RSTOOLS=true`** | injection output, CSV shape, submission responses |
| Cross-repo | local, `USE_RSTOOLS=true` + an RSTools build | **no** | the seam: schema built by RSTools, driven by FormShare |
| Device | KotlinCollect `IosFormShareEntityImportTest`, XCUITests | its own CI | import contract; offline register→follow-up; cross-restart persistence |

**CI cannot test this feature.** CircleCI runs ODKTools, which has no entity
support. What CI *does* prove is the regression case — that ODKTools deployments
are unaffected — and that is worth keeping green. The real gate is a documented
local run with `USE_RSTOOLS=true` against an RSTools build; treat that as a
release step, not an optional extra.

Fixtures already exist at `formshare/tests/resources/forms/case/`:
`case_start.xlsx`, `case_follow_up.xlsx`, `case_deactivate.xlsx`,
`case_activate.xlsx`, barcode variants, and `generated_case.csv`.

KotlinCollect's launch hooks in `RoundTrip.swift` (`-fs-seed-entity-list`,
`-fs-import-entity-csv`) drive device tests with no server, which keeps layer 4
fast.

### The four scenarios that matter

1. **Golden** — register offline, follow up offline, sync; both rows land,
   correctly linked, `rowuuid == __id`.
2. **Rejection** — case deactivated server-side while the device is offline; the
   follow-up is rejected with a readable message and is **not** retried.
3. **Identity** — a duplicate `__id` is rejected by the unique index; a non-v4
   id is replaced rather than stored.
4. **Regression** — non-case forms and existing case projects are unaffected.

### Risks to plan around

**Injection touches the upload path for every form.** Guard hard on
`project_case == 1`. Keep the user's original XLSX: FormShare stores and serves
it back for download, and the file the user gets must not be the injected one.

**`generated_case.csv` will break by design.** That fixture asserts today's
lookup CSV; adding `__version` and changing `name` changes it. That is a *good*
signal — do not let it be updated reflexively without someone checking the diff
is the intended one.

**Rollout: opt-in, new case projects only.** Two independent reasons now:
existing projects have `CaseLookUp.field_as = "name"` pointing at a user field,
and switching that to `rowuuid` changes what every existing follow-up form stores
as its selector; and their repositories still carry the **old v1 rowuuid
trigger**, since that change is DDL and RSTools has no migration for it
(their §6.5). A live repository would mint v1 ids that the device silently
refuses on create. Let the two models coexist and migrate later, if ever.

**Watch for a silent import abort.** S3 Q3: a missing `__version` column makes
the client discard the entire list with no error, and an empty or non-integer
value throws. A test should assert the CSV always carries an integer there —
this failure is invisible from the server side.
