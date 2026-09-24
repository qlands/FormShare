"""Actions: a form's decision table compiled to a JavaScript module, and the
host that runs such a module on the server.

docs/formshare_case_management/actions-api.md is the contract; decision 16 in
its README the reasoning. Three modules:

- ``compiler``: pure. The rows of the decision table, with the QueryBuilder
  rule set of each row's *when*, become the module of actions-api.md
  section 10 -- the same text the preview shows and the devices run.
- ``host``: pure with respect to the database. Runs a module in QuickJS
  over an input the caller assembled (the submission, the case, its parent,
  a lookup callback), collects the writes and the log, and never applies
  anything. What the golden triples exercise.
- ``server``: the glue. Assembles the input from a repository, validates
  the writes by type, applies them in one transaction with the audit user
  set, records the run, and offers the dry run.
"""
