from qgis_ltr_updater.version_check import VersionCheckError, parse_latest_version

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
