from pathlib import Path

from qgis_ltr_updater.installed import (
    InstallRecord,
    current_version,
    install_root_for,
    load_state,
    previous_version,
    save_state,
    scan_filesystem,
)


def test_save_and_load_state_roundtrip(tmp_path):
    state_file = tmp_path / "state.json"
    records = [
        InstallRecord(version="3.34.8-1", root="C:/OSGeo4W-QGIS-LTR-3.34.8-1", installed_at="2026-01-01T00:00:00+00:00"),
        InstallRecord(version="3.40.5-1", root="C:/OSGeo4W-QGIS-LTR-3.40.5-1", installed_at="2026-06-01T00:00:00+00:00"),
    ]
    save_state(records, state_file=state_file)

    loaded = load_state(state_file=state_file)
    assert [r.version for r in loaded] == ["3.34.8-1", "3.40.5-1"]


def test_load_state_missing_file_returns_empty(tmp_path):
    assert load_state(state_file=tmp_path / "missing.json") == []


def test_current_and_previous_version():
    records = [
        InstallRecord(version="3.34.8-1", root="r1", installed_at=""),
        InstallRecord(version="3.40.5-1", root="r2", installed_at=""),
    ]
    assert current_version(records) == "3.40.5-1"
    assert previous_version(records) == "3.34.8-1"


def test_current_and_previous_version_empty():
    assert current_version([]) is None
    assert previous_version([]) is None


def test_scan_filesystem_rebuilds_state(tmp_path):
    (tmp_path / "OSGeo4W-QGIS-LTR-3.34.8-1").mkdir()
    (tmp_path / "OSGeo4W-QGIS-LTR-3.40.5-1").mkdir()
    (tmp_path / "SomeOtherFolder").mkdir()

    records = scan_filesystem(install_root_parent=tmp_path, prefix="OSGeo4W-QGIS-LTR-")
    assert [r.version for r in records] == ["3.34.8-1", "3.40.5-1"]


def test_install_root_for():
    root = install_root_for("3.40.5-1", install_root_parent=Path("C:/Program Files"), prefix="OSGeo4W-QGIS-LTR-")
    assert str(root) == str(Path("C:/Program Files/OSGeo4W-QGIS-LTR-3.40.5-1"))
