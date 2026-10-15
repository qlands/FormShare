"""A project's logo: what is fixed, what is refused, and where it goes
(formshare/processes/project_logo.py, docs/project-logo.md). No database: the
images are made here, and the request is a stand-in."""

import io
import os
from types import SimpleNamespace

from PIL import Image, ImageCms
from PIL.PngImagePlugin import PngInfo

from formshare.processes import project_logo


def request():
    return SimpleNamespace(
        translate=lambda text: text,
        route_url=lambda name, **kw: "https://fs.example/project/{}/_fs_project_logo.png".format(
            kw["projectid"]
        ),
    )


def image_bytes(size, mode="RGBA", fmt="PNG", color=(10, 120, 200, 255), **save):
    image = Image.new(mode, size, color if mode != "P" else 0)
    output = io.BytesIO()
    image.save(output, fmt, **save)
    return output.getvalue()


def opened(png):
    return Image.open(io.BytesIO(png))


def test_a_logo_within_the_specification_is_kept_as_a_png():
    ok, png = project_logo.prepare_logo(request(), image_bytes((1200, 300)))
    assert ok
    image = opened(png)
    assert (image.format, image.size, image.mode) == ("PNG", (1200, 300), "RGBA")


def test_what_can_be_fixed_is_fixed():
    # Wider than 1600 px: scaled down, keeping its shape.
    ok, png = project_logo.prepare_logo(request(), image_bytes((2400, 600)))
    assert ok and opened(png).size == (1600, 400)
    # A WebP becomes a PNG.
    ok, png = project_logo.prepare_logo(
        request(), image_bytes((800, 200), fmt="WEBP", lossless=True)
    )
    assert ok and opened(png).format == "PNG"
    # Metadata and a colour profile are dropped, the colours kept in sRGB.
    info = PngInfo()
    info.add_text("Comment", "made by someone")
    srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    ok, png = project_logo.prepare_logo(
        request(), image_bytes((800, 200), pnginfo=info, icc_profile=srgb)
    )
    assert ok
    assert "Comment" not in opened(png).info
    assert "icc_profile" not in opened(png).info
    # A palette image keeps its palette and its transparency.
    palette = Image.new("P", (900, 300), 0)
    palette.putpalette([255, 255, 255, 200, 30, 30] + [0] * 762)
    output = io.BytesIO()
    palette.save(output, "PNG", transparency=0)
    ok, png = project_logo.prepare_logo(request(), output.getvalue())
    assert ok and opened(png).mode == "P"
    assert "transparency" in opened(png).info


def test_what_cannot_be_fixed_is_refused_saying_why():
    def refused(data):
        ok, message = project_logo.prepare_logo(request(), data)
        assert not ok
        return message

    assert "JPEG" in refused(image_bytes((1200, 300), mode="RGB", fmt="JPEG"))
    assert "GIF" in refused(image_bytes((1200, 300), mode="P", fmt="GIF"))
    assert "300 × 600" in refused(image_bytes((300, 600)))
    assert "1400 × 200" in refused(image_bytes((1400, 200)))
    assert "150 px tall" in refused(image_bytes((600, 150)))
    assert "read" in refused(b"not an image at all")
    # An animated PNG.
    frames = [Image.new("RGBA", (800, 200), c) for c in ("red", "blue")]
    output = io.BytesIO()
    frames[0].save(output, "PNG", save_all=True, append_images=frames[1:])
    assert "animated" in refused(output.getvalue())
    # Heavier than 200 KB once optimised: noise does not compress.
    noise = Image.frombytes("RGBA", (1200, 300), os.urandom(1200 * 300 * 4))
    output = io.BytesIO()
    noise.save(output, "PNG")
    assert "KB" in refused(output.getvalue())
    # More than 10 MB is not even opened.
    assert "10 MB" in refused(b"0" * (project_logo.MAX_UPLOAD_BYTES + 1))


def test_an_empty_file_input_is_no_upload():
    assert project_logo.uploaded_file(None) is None
    assert project_logo.uploaded_file("") is None
    assert project_logo.uploaded_file(SimpleNamespace(filename="")) is None
    chosen = SimpleNamespace(filename="logo.png")
    assert project_logo.uploaded_file(chosen) is chosen


def test_the_qr_s_project_section_names_the_logo_only_when_there_is_one():
    details = {
        "project_id": "p-1",
        "project_name": "Farms",
        "project_icon": "🌱",
        "project_hexcolor": "#00ff00",
        "project_logo_md5": None,
    }
    assert project_logo.collect_project_section(request(), details) == {
        "name": "Farms",
        "icon": "🌱",
        "color": "#00ff00",
    }
    details["project_logo_md5"] = "abc123"
    section = project_logo.collect_project_section(request(), details)
    assert section["logo_url"] == "https://fs.example/project/p-1/_fs_project_logo.png"
    assert section["logo_md5"] == "abc123"


def test_the_manifest_carries_the_logo_only_when_there_is_one(monkeypatch):
    logo = {"md5": None}
    monkeypatch.setattr(
        project_logo, "get_project_logo_md5", lambda req, project: logo["md5"]
    )
    assert project_logo.logo_manifest_entries(request(), "p-1", []) == []
    logo["md5"] = "abc123"
    assert project_logo.logo_manifest_entries(request(), "p-1", None) == [
        {
            "filename": "_fs_project_logo.png",
            "hash": "md5:abc123",
            "downloadUrl": "https://fs.example/project/p-1/_fs_project_logo.png",
        }
    ]
    # A form with a media file of that name of its own keeps it.
    own = [{"file_name": "_fs_project_logo.png", "file_md5": "zzz"}]
    assert project_logo.logo_manifest_entries(request(), "p-1", own) == []


def test_other_colour_modes_come_out_as_rgb_or_rgba():
    def mode_of(image):
        output = io.BytesIO()
        image.save(output, "PNG")
        ok, png = project_logo.prepare_logo(request(), output.getvalue())
        assert ok
        return opened(png).mode, opened(png).size

    assert mode_of(Image.new("L", (800, 200), 128)) == ("RGB", (800, 200))
    assert mode_of(Image.new("LA", (800, 200), (128, 100))) == ("RGBA", (800, 200))
    # A palette image that must be scaled down is scaled in full colour.
    palette = Image.new("P", (2400, 600), 1)
    palette.putpalette([255, 255, 255, 200, 30, 30] + [0] * 762)
    assert mode_of(palette) == ("RGB", (1600, 400))


def test_an_image_too_large_to_decode_is_refused_before_it_is():
    """A PNG whose header claims 6000 × 5000 px: refused from the header,
    without decoding thirty million pixels."""
    import struct
    import zlib

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 6000, 5000, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\x00" * 64))
        + chunk(b"IEND", b"")
    )
    ok, message = project_logo.prepare_logo(request(), png)
    assert not ok and "read" in message


def test_a_logo_missing_from_the_storage_reads_as_none(monkeypatch):
    monkeypatch.setattr(project_logo, "get_stream", lambda req, bucket, name: None)
    assert project_logo.read_project_logo(request(), "p-1") is None
