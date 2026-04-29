import pytest

from build import release_config


def test_artifact_directory_name_contains_version_and_os(monkeypatch):
    monkeypatch.setattr(release_config.platform, "machine", lambda: "AMD64")

    assert (
        release_config.artifact_directory_name("windows")
        == "numeric-workbench-v1.0-windows-x86_64"
    )


def test_validate_target_os_rejects_unsupported():
    with pytest.raises(ValueError, match="Unsupported OS"):
        release_config.validate_target_os("solaris")


def test_validate_target_os_requires_native_build(monkeypatch):
    monkeypatch.setattr(release_config, "current_os_name", lambda: "windows")

    with pytest.raises(ValueError, match="must be created natively"):
        release_config.validate_target_os("linux")
