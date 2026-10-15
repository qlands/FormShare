"""A project's logo, which FormShare Collect shows on its main menu
(docs/project-logo.md).

An owner uploads it in the project form. It is checked against what the apps
can show: a PNG, from square to 6:1, at least 192 px tall, at most 1600 px wide
and 200 KB. What can be fixed without losing anything is fixed -- a wider image
is scaled down, a WebP becomes a PNG, colours are brought to sRGB, metadata is
dropped and the PNG optimised -- and anything else outside those bounds is
refused, saying which bound and by how much. SVG is not accepted: no renderer
is installed, and the apps take PNG only.

The storage keeps the image in the project's bucket under one name, and
project.project_logo_md5 says which image it is. It reaches devices three ways:

- a public URL, /project/<project id>/_fs_project_logo.png, whose ETag is the MD5;
- the project section of the QR codes (the project's and an assistant's), as
  logo_url and logo_md5;
- every form's manifest, as the media file _fs_project_logo.png, so that a new
  logo comes down with the next form update.

A project without a logo gets exactly what it got before: no QR key, no
manifest entry.
"""

import io
from hashlib import md5

from PIL import Image, ImageCms, ImageOps, UnidentifiedImageError

from formshare.processes.db.project import (
    get_project_logo_md5,
    set_project_logo_md5,
)
from formshare.processes.storage import delete_stream, get_stream, store_file

LOGO_FILE_NAME = "_fs_project_logo.png"
LOGO_ROUTE = "project_logo"

ACCEPTED_FORMATS = ("PNG", "WEBP")
MIN_HEIGHT = 192  # the slot is 64 points tall, and phones draw 3 px a point
MAX_WIDTH = 1600
MAX_RATIO = 6  # width over height
MAX_BYTES = 200 * 1024  # field devices are often on weak connections
# What is read of an upload, and how many pixels are decoded, at most: an
# image that would decompress to much more is refused before it is.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 25_000_000


def uploaded_file(value):
    """The file a file input sent, or None when nothing was chosen: an empty
    input still arrives, with an empty file name."""
    if value is None or isinstance(value, str):
        return None
    if str(getattr(value, "filename", "") or "").strip() == "":
        return None
    return value


def read_upload(upload):
    """The bytes of an upload, at most one more than MAX_UPLOAD_BYTES."""
    upload.file.seek(0)
    return upload.file.read(MAX_UPLOAD_BYTES + 1)


def _in_srgb(image):
    """The image in sRGB when it carries a colour profile of its own; as it is
    when it does not, or when the profile cannot be read."""
    profile = image.info.get("icc_profile")
    if not profile or image.mode not in ("RGB", "RGBA"):
        return image
    try:
        source = ImageCms.ImageCmsProfile(io.BytesIO(profile))
        return ImageCms.profileToProfile(
            image, source, ImageCms.createProfile("sRGB"), outputMode=image.mode
        )
    except (ImageCms.PyCMSError, OSError, ValueError):
        return image


def prepare_logo(request, data):
    """(True, PNG bytes) for an image the apps can show, once fixed;
    (False, why not) for one that cannot be fixed without losing something."""
    _ = request.translate
    if len(data) > MAX_UPLOAD_BYTES:
        return False, _("The logo file is larger than 10 MB.")
    unreadable = _("The logo is not an image FormShare can read. Upload a PNG.")
    try:
        image = Image.open(io.BytesIO(data))
    except (UnidentifiedImageError, OSError, ValueError):
        return False, unreadable
    if image.format not in ACCEPTED_FORMATS:
        return False, _(
            "The logo must be a PNG (a WebP is converted). This file is a {}."
        ).format(image.format)
    if getattr(image, "n_frames", 1) > 1:
        return False, _("The logo cannot be animated.")
    width, height = image.size
    if width * height > MAX_PIXELS:
        return False, unreadable
    try:
        image.load()
        # A camera's orientation tag turns the picture the way its owner saw it.
        image = ImageOps.exif_transpose(image)
    except (OSError, ValueError, Image.DecompressionBombError):
        return False, unreadable

    width, height = image.size
    if width < height:
        return False, _(
            "The logo is {} × {} px: taller than it is wide. It must be from "
            "square (1:1) to six times as wide as it is tall, such as 1200 × 300 px."
        ).format(width, height)
    if width > MAX_RATIO * height:
        return False, _(
            "The logo is {} × {} px: more than six times as wide as it is tall. "
            "It must be from square (1:1) to 6:1, such as 1200 × 300 px."
        ).format(width, height)
    if height < MIN_HEIGHT:
        return False, _(
            "The logo is {} px tall. It must be at least {} px tall to stay sharp "
            "on a phone."
        ).format(height, MIN_HEIGHT)

    # A palette image that needs no scaling keeps its palette: as a full
    # colour PNG it could come out heavier than it went in.
    resize = width > MAX_WIDTH
    if image.mode != "P" or resize:
        if image.mode not in ("RGB", "RGBA"):
            transparent = (
                image.mode in ("LA", "PA", "RGBa")
                or "transparency" in image.info
                or image.mode.endswith("A")
            )
            image = image.convert("RGBA" if transparent else "RGB")
        image = _in_srgb(image)
        if resize:
            image = image.resize(
                (MAX_WIDTH, round(height * MAX_WIDTH / width)), Image.LANCZOS
            )

    # The colours are sRGB now, which is what a PNG without a profile means:
    # the profile ImageCms attached, or the palette image's, is not kept.
    image.info.pop("icc_profile", None)
    output = io.BytesIO()
    image.save(output, "PNG", optimize=True)
    png = output.getvalue()
    if len(png) > MAX_BYTES:
        return False, _(
            "The logo is {} KB as a PNG. It must be at most 200 KB: fewer colours "
            "or a smaller canvas make it lighter."
        ).format(round(len(png) / 1024))
    return True, png


def save_project_logo(request, project_id, png):
    """Stores a prepared logo and records its MD5. Returns the MD5."""
    store_file(request, project_id, LOGO_FILE_NAME, io.BytesIO(png))
    logo_md5 = md5(png).hexdigest()
    set_project_logo_md5(request, project_id, logo_md5)
    return logo_md5


def remove_project_logo(request, project_id):
    """Removes the project's logo, if it has one."""
    delete_stream(request, project_id, LOGO_FILE_NAME)
    set_project_logo_md5(request, project_id, None)


def read_project_logo(request, project_id):
    """The bytes of the project's logo, or None."""
    stream = get_stream(request, project_id, LOGO_FILE_NAME)
    if stream is None:
        return None
    try:
        return stream.read()
    finally:
        stream.close()


def logo_url(request, project_id):
    """The public address of a project's logo."""
    return request.route_url(LOGO_ROUTE, projectid=project_id)


def collect_project_section(request, project_details):
    """The "project" section of an ODK Collect QR: the project's name, emoji
    and colour, and its logo's address and MD5 when it has one."""
    section = {
        "name": project_details["project_name"],
        "icon": project_details["project_icon"],
        "color": project_details["project_hexcolor"],
    }
    if project_details.get("project_logo_md5"):
        section["logo_url"] = logo_url(request, project_details["project_id"])
        section["logo_md5"] = project_details["project_logo_md5"]
    return section


def logo_manifest_entries(request, project_id, form_files=None):
    """The manifest entry of the project's logo: none when the project has
    no logo, so its manifests stay as they were, or when the form has a media
    file of that name of its own."""
    logo_md5 = get_project_logo_md5(request, project_id)
    if not logo_md5:
        return []
    for a_file in form_files or []:
        if a_file.get("file_name") == LOGO_FILE_NAME:
            return []
    return [
        {
            "filename": LOGO_FILE_NAME,
            "hash": "md5:" + logo_md5,
            "downloadUrl": logo_url(request, project_id),
        }
    ]
