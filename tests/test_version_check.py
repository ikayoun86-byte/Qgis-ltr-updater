from qgis_ltr_updater import version_check
from qgis_ltr_updater.version_check import (
    VersionCheckError,
    find_snapshot_for_version,
    get_ltr_series,
    list_snapshot_dates,
    parse_latest_version,
)

SAMPLE_SETUP_INI = """\
@ qgis
sdesc: "QGIS Desktop (latest)"
category: Desktop
version: 3.44.1-1
install: x86_64/release/qgis/qgis/qgis-3.44.1-1.tar.zst 12345 abcdef
source: x86_64/release/qgis/qgis/qgis-3.44.1-1-src.tar.zst 999 abcdef
[test]
version: 3.45.0-1
install: x86_64/release/qgis/qgis/qgis-3.45.0-1.tar.zst 12345 abcdef

@ qgis-ltr-full
sdesc: "QGIS LTR full meta-package"
category: Desktop
version: 3.40.5-1
install: x86_64/release/qgis/qgis-ltr-full/qgis-ltr-full-3.40.5-1.tar.zst 111 abcdef
source: x86_64/release/qgis/qgis-ltr-full/qgis-ltr-full-3.40.5-1-src.tar.zst 222 abcdef
[test]
version: 3.40.6-1
install: x86_64/release/qgis/qgis-ltr-full/qgis-ltr-full-3.40.6-1.tar.zst 111 abcdef

@ gdal
sdesc: "GDAL library"
category: Libs
version: 3.9.0-1
install: x86_64/release/gdal/gdal-3.9.0-1.tar.zst 333 abcdef
"""


def test_parse_latest_version_finds_stable_release():
    assert parse_latest_version(SAMPLE_SETUP_INI, "qgis-ltr-full") == "3.40.5-1"


def test_parse_latest_version_ignores_test_channel():
    # La version [test] (3.40.6-1) ne doit jamais être choisie.
    version = parse_latest_version(SAMPLE_SETUP_INI, "qgis-ltr-full")
    assert version != "3.40.6-1"


def test_parse_latest_version_different_package():
    assert parse_latest_version(SAMPLE_SETUP_INI, "gdal") == "3.9.0-1"


def test_parse_latest_version_missing_package_raises():
    try:
        parse_latest_version(SAMPLE_SETUP_INI, "does-not-exist")
    except VersionCheckError:
        pass
    else:
        raise AssertionError("VersionCheckError attendue")


class _FakeResponse:
    def __init__(self, payload=None, text=None):
        self._payload = payload
        self.text = text

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


FAKE_GITHUB_RELEASES = [
    {"tag_name": "final-3_40_10", "published_at": "2026-01-08T00:00:00Z"},
    {"tag_name": "final-3_40_9", "published_at": "2025-11-01T00:00:00Z"},
    {"tag_name": "final-3_34_15", "published_at": "2025-08-06T00:00:00Z"},
    {"tag_name": "final-3_34_14", "published_at": "2025-06-01T00:00:00Z"},
    {"tag_name": "final-3_38_2", "published_at": "2025-09-01T00:00:00Z"},  # pas une série LTR
    {"tag_name": "not-a-version-tag", "published_at": "2025-01-01T00:00:00Z"},
]


def test_get_ltr_series_keeps_latest_patch_per_minor(monkeypatch):
    monkeypatch.setattr(
        version_check.requests, "get", lambda *a, **k: _FakeResponse(payload=FAKE_GITHUB_RELEASES)
    )
    series = get_ltr_series()
    assert [entry["version"] for entry in series] == ["3.40.10", "3.34.15"]


def test_get_ltr_series_respects_limit(monkeypatch):
    monkeypatch.setattr(
        version_check.requests, "get", lambda *a, **k: _FakeResponse(payload=FAKE_GITHUB_RELEASES)
    )
    series = get_ltr_series(limit=1)
    assert len(series) == 1
    assert series[0]["version"] == "3.40.10"


def test_snapshot_dir_regex_extracts_dates():
    html = """
    <html><body>
    <a href="2025-08-01/">2025-08-01/</a>
    <a href="2025-08-15/">2025-08-15/</a>
    <a href="../">../</a>
    </body></html>
    """

    def fake_get(url, timeout=20):
        return _FakeResponse(text=html)

    import qgis_ltr_updater.version_check as vc
    original = vc.requests.get
    vc.requests.get = fake_get
    try:
        dates = list_snapshot_dates()
    finally:
        vc.requests.get = original
    assert dates == ["2025-08-01", "2025-08-15"]


def test_find_snapshot_for_version_returns_first_match(monkeypatch):
    monkeypatch.setattr(version_check, "list_snapshot_dates", lambda: ["2025-08-01", "2025-08-15", "2025-09-01"])

    ini_by_date = {
        "2025-08-01": SAMPLE_SETUP_INI,  # qgis-ltr-full = 3.40.5-1 ici
    }

    def fake_fetch_setup_ini(urls=None, timeout=15):
        for date, ini in ini_by_date.items():
            if date in urls[0]:
                return ini
        raise VersionCheckError("pas de snapshot pour cette date")

    monkeypatch.setattr(version_check, "fetch_setup_ini", fake_fetch_setup_ini)

    site, version = find_snapshot_for_version("3.40.5")
    assert site == f"{version_check.config.SNAPSHOTS_INDEX_URL}2025-08-01"
    assert version == "3.40.5-1"


def test_find_snapshot_for_version_no_match_returns_none(monkeypatch):
    monkeypatch.setattr(version_check, "list_snapshot_dates", lambda: ["2025-08-01"])
    monkeypatch.setattr(
        version_check, "fetch_setup_ini", lambda urls=None, timeout=15: SAMPLE_SETUP_INI
    )

    site, version = find_snapshot_for_version("9.99.99")
    assert site is None
    assert version is None
