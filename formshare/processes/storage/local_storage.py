import logging
from formshare.processes.logging.loggerclass import SecretLogger
import formshare.plugins as plugins
import mimetypes
import os
import uuid
from ofs.base import BucketExists
from ofs.local import PTOFS
from pairtree import FileNotFoundException
from pairtree import PairtreeStorageClient, ObjectNotFoundException

__all__ = [
    "store_file",
    "get_stream",
    "response_stream",
    "delete_stream",
    "delete_bucket",
    "get_temporary_directory",
    "get_temporary_file",
]

_BLOCK_SIZE = 4096 * 64  # 256K

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")


def get_temporary_directory(request):
    repository_path = request.registry.settings["repository.path"]
    return os.path.join(repository_path, *["tmp", str(uuid.uuid4())])


def get_temporary_file(request, extension):
    tmp_id = str(uuid.uuid4())
    repository_path = request.registry.settings["repository.path"]
    dir_path = os.path.join(repository_path, *["tmp", tmp_id])
    os.makedirs(dir_path)
    return os.path.join(
        repository_path, *["tmp", tmp_id, tmp_id + "." + extension.lower()]
    )


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
    for a_plugin in plugins.PluginImplementations(plugins.IFileStorage):
        a_plugin.on_storing_file(
            request, storage_object, bucket_id, file_name, file_buffer
        )
    storage_object.put_stream(bucket_id, file_name, file_buffer)


def delete_stream(request, bucket_id, file_name):
    storage_object = get_storage_object(request)
    try:
        for a_plugin in plugins.PluginImplementations(plugins.IFileStorage):
            a_plugin.on_removing_file(request, storage_object, bucket_id, file_name)
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
        for a_plugin in plugins.PluginImplementations(plugins.IFileStorage):
            a_plugin.on_removing_bucket(request, storage_object, bucket_id)
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
    except OSError as e:
        # A form file recorded under an empty name resolves to the bucket's
        # own directory, and opening it raises IsADirectoryError. The caller
        # asked whether the file is there; it is not, and saying so is better
        # than taking down the page that lists it.
        log.error(
            "Unable to read '{}' from bucket {}. Error: {}".format(
                file_name, bucket_id, str(e)
            )
        )
    return None


def response_stream(stream, file_name, response, unique_filename=None):
    from starlette.responses import StreamingResponse

    content_type, content_enc = mimetypes.guess_type(file_name)
    if content_type is None:
        content_type = "application/binary"

    download_name = unique_filename if unique_filename is not None else file_name

    stream.seek(0, 2)
    file_size = stream.tell()
    stream.seek(0)

    headers = {
        "Content-Disposition": 'attachment; filename="{}"'.format(download_name),
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
        "Content-Length": str(file_size),
    }

    return StreamingResponse(
        FileIter(stream, _BLOCK_SIZE),
        media_type=content_type,
        headers=headers,
    )


class FileIter(object):
    """A fixed-block-size iterator for use as a WSGI app_iter. Based on Pyramid FileResponse

    file: is a Python file pointer (or at least an object with a ``read`` method that takes a size hint).
    block_size: is an optional block size for iteration.
    """

    def __init__(self, file_pointer, block_size=_BLOCK_SIZE):
        self.file = file_pointer
        self.block_size = block_size

    def __iter__(self):
        return self

    def __next__(self):
        val = self.file.read(self.block_size)
        if not val:
            raise StopIteration
        return val

    def close(self):
        self.file.close()
