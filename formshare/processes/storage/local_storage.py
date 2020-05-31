import logging
import mimetypes
import os

from ofs.base import BucketExists
from ofs.local import PTOFS
from pairtree import FileNotFoundException
from pairtree import PairtreeStorageClient, ObjectNotFoundException

__all__ = [
    "store_file",
    "get_stream",
    "response_stream",
    "stream_exists",
    "delete_stream",
    "delete_bucket",
]

_BLOCK_SIZE = 4096 * 64  # 256K

log = logging.getLogger("formshare")


def get_storage_object(request):
    repository_path = request.registry.settings["repository.path"]
    if not os.path.exists(repository_path):
        os.makedirs(repository_path)
    storage_path = os.path.join(repository_path, *["storage"])
    return PTOFS(storage_dir=storage_path)


def store_file(request, bucket_id, file_name, file_buffer):
    storage_object = get_storage_object(request)
    try:
        storage_object.claim_bucket(bucket_id)
    except BucketExists:
        pass
    storage_object.put_stream(bucket_id, file_name, file_buffer)


def delete_stream(request, bucket_id, file_name):
    storage_object = get_storage_object(request)
    try:
        storage_object.del_stream(bucket_id, file_name)
        return True
    except FileNotFoundException:
        return False


def delete_bucket(
    request, bucket_id, uri_base="urn:uuid:", hashing_type="md5", shorty_length=2
):
    try:
        repository_path = request.registry.settings["repository.path"]
        if not os.path.exists(repository_path):
            os.makedirs(repository_path)
        storage_path = os.path.join(repository_path, *["storage"])
        storage_object = PairtreeStorageClient(
            uri_base,
            storage_path,
            shorty_length=shorty_length,
            hashing_type=hashing_type,
        )
        storage_object.delete_object(bucket_id)
    except ObjectNotFoundException:
        return
    except Exception as e:
        log.error("Error {} while deleting buckeid form {}".format(str(e), bucket_id))


def get_stream(request, bucket_id, file_name):
    storage_object = get_storage_object(request)
    try:
        storage_object.claim_bucket(bucket_id)
    except BucketExists:
        pass
    try:
        res = storage_object.get_stream(bucket_id, file_name)
        return res
    except FileNotFoundException:
        pass
    return None


def stream_exists(request, bucket_id, file_name):
    storage_object = get_storage_object(request)
    try:
        storage_object.claim_bucket(bucket_id)
    except BucketExists:
        pass
    try:
        stream = storage_object.get_stream(bucket_id, file_name)
        stream.seek(0, 2)
        file_size = stream.tell()
        stream.close()
        return file_size
    except FileNotFoundException:
        pass
    return -1


def response_stream(stream, file_name, response):
    content_type, content_enc = mimetypes.guess_type(file_name)
    if content_type is None:
        content_type = "application/binary"
    response.headers["Content-Type"] = content_type
    response.content_disposition = 'attachment; filename="' + file_name + '"'
    stream.seek(0, 2)
    file_size = stream.tell()
    stream.seek(0)
    response.app_iter = FileIter(stream, _BLOCK_SIZE)
    response.content_length = file_size
    return response


class FileIter(object):
    """ A fixed-block-size iterator for use as a WSGI app_iter. Based on Pyramid FileResponse

    file: is a Python file pointer (or at least an object with a ``read`` method that takes a size hint).
    block_size: is an optional block size for iteration.
    """

    def __init__(self, file_pointer, block_size=_BLOCK_SIZE):
        self.file = file_pointer
        self.block_size = block_size

    def __iter__(self):
        return self

    def next(self):
        val = self.file.read(self.block_size)
        if not val:
            raise StopIteration
        return val

    __next__ = next  # py3

    def close(self):
        self.file.close()


def _guess_type(path):
    content_type, content_encoding = mimetypes.guess_type(path, strict=False)
    if content_type is None:
        content_type = "application/octet-stream"
    # str-ifying content_type is a workaround for a bug in Python 2.7.7
    # on Windows where mimetypes.guess_type returns unicode for the
    # content_type.
    content_type = str(content_type)
    return content_type, content_encoding
