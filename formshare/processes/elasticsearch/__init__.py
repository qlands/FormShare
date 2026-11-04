"""FormShare's Elasticsearch indexes: the datasets (submissions), the
records, the users and the partners."""

# How many times a deletion by query is tried, when documents change under it
DELETE_ATTEMPTS = 5


class DeletionConflict(Exception):
    """Documents kept changing while a deletion by query removed them."""


def delete_matching(connection, index, body):
    """Deletes every document of the index that the query in body matches,
    and returns what Elasticsearch said of the last attempt.

    A deletion by query reads the index as of its last refresh, and deletes
    each document by the version it read. A document indexed or changed
    since is a version conflict, and by default the request stops there with
    a 409, part of the deletion done. "Delete all submissions" right after a
    submission arrived did that (CI builds 904 and 906, 2026-10-31 and
    2026-11-03), and said it had failed while the repository was already
    empty. So the index is refreshed first, a conflict does not stop the
    request, and what conflicted is deleted again, on a fresh read. The
    deletions are visible when this returns."""
    for _attempt in range(DELETE_ATTEMPTS):
        connection.indices.refresh(index=index)
        result = connection.delete_by_query(
            index=index, body=body, conflicts="proceed", refresh=True
        )
        found = getattr(result, "body", result) or {}
        if not found.get("version_conflicts"):
            return found
    raise DeletionConflict(
        "Documents of the index {} kept changing while they were deleted: {} "
        "attempts".format(index, DELETE_ATTEMPTS)
    )
