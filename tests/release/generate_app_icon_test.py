from pathlib import Path

from build import generate_app_icon


def test_generate_windows_icon_creates_ico_file(tmp_path: Path, monkeypatch):
    target = tmp_path / "app.ico"
    payloads = {
        16: b"png16",
        24: b"png24",
        32: b"png32",
        48: b"png48",
        64: b"png64",
        128: b"png128",
        256: b"png256",
    }

    monkeypatch.setattr(
        generate_app_icon,
        "_render_png_payload_windows",
        lambda size: payloads[size],
    )

    generate_app_icon.generate_windows_icon(target)

    payload = target.read_bytes()
    assert target.exists()
    assert payload[:4] == b"\x00\x00\x01\x00"
    assert len(payload) > len(b"".join(payloads.values()))
