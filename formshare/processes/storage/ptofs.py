"""PTOFS, the store of FormShare's files, taken from ofs 0.4.3.

ofs (http://github.com/okfn/ofs) is by Ben O'Steen, Friedrich Lindenberg and
Rufus Pollock, under the Apache License, Version 2.0: LICENSE-ofs.txt, beside
this file. Its last release, 0.4.3, is from 2018-03-22, and it imports
pkg_resources when it loads. setuptools 81 removed pkg_resources, so with a
current setuptools FormShare could not even be imported
(formshare_enterprise:20261018). FormShare uses one class of ofs, so the class
is here, with the changes below.

- PTOFS (ofs/local/pairtreestore.py) and PersistentState
  (ofs/local/storedjson.py) are as they were, but for:
  - the OFSInterface base class and ofs's backend registry are gone;
  - _open_store without hashing named an undefined shorty_length;
  - put_stream took a mutable default;
  - get_url is gone: it called a method pairtree does not have, so it never
    worked;
  - PersistentState logs where it printed;
  - Python 2 leftovers (__cmp__, simplejson, __future__ imports) are gone.
- BucketExists is ofs's exception (ofs/base.py).

Nothing about the files changes. pairtree still lays them out
(storage/pairtree_root/, a folder per bucket), and each bucket's
persisted_state.json is written as ofs wrote it, so every file stored before
reads the same. Plugins get a PTOFS in IFileStorage's hooks, as before,
with the same methods but get_url.
"""

import json
import logging
from datetime import datetime
from os import path
from uuid import uuid4

from pairtree import FileNotFoundException, PairtreeStorageClient

__all__ = ["PTOFS", "PersistentState", "BucketExists"]

log = logging.getLogger("formshare")

PERSISTENCE_FILENAME = "persisted_state.json"


class BucketExists(Exception):
    """A bucket claimed by name is there already."""


class PersistentState(object):
    """A bucket's record of its files, kept as JSON in the bucket's folder:
    for each file its label, size, creation and modification dates and MD5."""

    def __init__(self, filepath=None, filename=PERSISTENCE_FILENAME, create=True):
        self.state = {}
        self.filepath = None
        if filepath:
            self.set_filepath(filepath, filename, create)
        self.revert()

    def set_filepath(self, filepath, filename=PERSISTENCE_FILENAME, create=True):
        if path.isdir(filepath):
            self.filepath = path.join(filepath, filename)
            if create and not path.isfile(self.filepath):
                self.sync()
            return True
        log.error(
            "The folder {} does not exist: its record of files cannot be "
            "kept".format(filepath)
        )
        return False

    def revert(self):
        """The state as the file has it."""
        if not self.filepath:
            log.error("The record of a bucket's files has no path to be read from")
            return False
        if not path.isfile(self.filepath):
            log.error("The record of files {} does not exist yet".format(self.filepath))
            return False
        with open(self.filepath, "r") as serialised_file:
            try:
                self.state = json.load(serialised_file)
            except ValueError:
                log.error(
                    "The record of files {} holds no JSON: it may be "
                    "empty".format(self.filepath)
                )
                self.state = {}
        return True

    def sync(self):
        """Writes the state to the file."""
        if not self.filepath:
            log.error("The record of a bucket's files has no path to be written to")
            return
        with open(self.filepath, "w") as serialised_file:
            json.dump(self.state, serialised_file)

    # Dictionary methods
    def keys(self):
        return self.state.keys()

    def has_key(self, key):
        return key in self.state

    def items(self):
        return self.state.items()

    def values(self):
        return self.state.values()

    def clear(self):
        self.state.clear()

    def update(self, kw):
        for key in kw:
            self.state[key] = kw[key]

    def __setitem__(self, key, item):
        self.state[key] = item

    def __getitem__(self, key):
        return self.state[key]

    def __repr__(self):
        return repr(self.state)

    def __len__(self):
        return len(self.state)

    def __delitem__(self, key):
        del self.state[key]


class PTOFS(object):
    """Buckets of files on the file system, laid out by pairtree
    (https://pypi.org/project/Pairtree/)."""

    def __init__(
        self,
        storage_dir="data",
        uri_base="urn:uuid:",
        hashing_type="md5",
        shorty_length=2,
    ):
        self.storage_dir = storage_dir
        self.uri_base = uri_base
        self.hashing_type = hashing_type
        self.shorty_length = shorty_length
        self._open_store()

    def _open_store(self):
        if self.hashing_type:
            self._store = PairtreeStorageClient(
                self.uri_base,
                self.storage_dir,
                shorty_length=self.shorty_length,
                hashing_type=self.hashing_type,
            )
        else:
            self._store = PairtreeStorageClient(
                self.uri_base, self.storage_dir, shorty_length=self.shorty_length
            )

    def exists(self, bucket, label=None):
        if self._store.exists(bucket):
            if label:
                return self._store.isfile(bucket, label)
            return True

    def _get_object(self, bucket):
        po = self._store.get_object(bucket)
        json_payload = PersistentState(po.id_to_dirpath())
        return po, json_payload

    def _setup_item(self, bucket):
        _, json_payload = self._get_object(bucket)
        json_payload.sync()

    def claim_bucket(self, bucket=None):
        if bucket:
            if self.exists(bucket):
                raise BucketExists
        else:
            bucket = uuid4().hex
            while self.exists(bucket):
                bucket = uuid4().hex
        self._setup_item(bucket)
        return bucket

    def list_labels(self, bucket):
        if self.exists(bucket):
            _, json_payload = self._get_object(bucket)
            return json_payload.keys()

    def list_buckets(self):
        return self._store.list_ids()

    def put_stream(self, bucket, label, stream_object, params=None):
        # The bucket need not have been claimed first
        params = params or {}
        po, json_payload = self._get_object(bucket)

        if label in json_payload.keys():
            creation_date = None
        else:
            # A new file: its creation date, as '2010-07-08T19:56:47'
            creation_date = datetime.now().isoformat().split(".")[0]
            if "_label" in params:
                json_payload[label] = {"_label": params["_label"]}
            else:
                json_payload[label] = {"_label": label}

        hash_vals = po.add_bytestream_by_path(label, stream_object)
        stat_vals = po.stat(label)

        # The caller's own parameters for the file
        cleaned_params = dict([(k, params[k]) for k in params if not k.startswith("_")])
        json_payload[label].update(cleaned_params)
        try:
            json_payload[label]["_content_length"] = int(stat_vals.st_size)
        except TypeError:
            log.error("The size of {} in {} is not a number".format(label, bucket))
        if creation_date:
            json_payload[label]["_creation_date"] = creation_date
            json_payload[label]["_last_modified"] = creation_date
        else:
            json_payload[label]["_last_modified"] = (
                datetime.now().isoformat().split(".")[0]
            )
        if hash_vals:
            json_payload[label]["_checksum"] = "%s:%s" % (
                hash_vals["type"],
                hash_vals["checksum"],
            )
        json_payload.sync()
        return json_payload.state[label]

    def get_stream(self, bucket, label, as_stream=True):
        if self.exists(bucket):
            po, json_payload = self._get_object(bucket)
            if self.exists(bucket, label):
                return po.get_bytestream(
                    label, streamable=as_stream, path=None, appendable=False
                )
        raise FileNotFoundException

    def get_metadata(self, bucket, label):
        if self.exists(bucket):
            _, json_payload = self._get_object(bucket)
            if json_payload.has_key(label):
                return json_payload.state[label]
        raise FileNotFoundException

    def update_metadata(self, bucket, label, params):
        if self.exists(bucket, label) and isinstance(params, dict):
            _, json_payload = self._get_object(bucket)
            # The caller's own parameters for the file
            cleaned_params = dict(
                [(k, params[k]) for k in params if not k.startswith("_")]
            )
            json_payload[label].update(cleaned_params)
            json_payload.sync()
            return json_payload.state[label]
        raise FileNotFoundException

    def del_metadata_keys(self, bucket, label, keys):
        if self.exists(bucket, label) and isinstance(keys, list):
            _, json_payload = self._get_object(bucket)
            for key in [x for x in keys if not x.startswith("_")]:
                if key in json_payload[label].keys():
                    del json_payload[label][key]
            json_payload.sync()
            return json_payload.state[label]
        raise FileNotFoundException

    def del_stream(self, bucket, label):
        if self.exists(bucket, label):
            self._store.del_stream(bucket, label)
            _, json_payload = self._get_object(bucket)
            if json_payload.has_key(label):
                del json_payload[label]
            json_payload.sync()
        else:
            raise FileNotFoundException
