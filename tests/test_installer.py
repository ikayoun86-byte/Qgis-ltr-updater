from qgis_ltr_updater.installer import uninstall_version


def test_uninstall_version_removes_root_and_shortcuts(tmp_path):
    root_dir = tmp_path / "OSGeo4W-QGIS-LTR-3.34.8-1"
    root_dir.mkdir()
    (root_dir / "bin").mkdir()
    (root_dir / "bin" / "qgis-ltr-bin.exe").write_text("fake")

    start_menu_a = tmp_path / "start_menu_all_users"
    start_menu_b = tmp_path / "start_menu_current_user"
    start_menu_a.mkdir()
    start_menu_b.mkdir()
    (start_menu_a / "QGIS LTR 3.34.8-1").mkdir()

    uninstall_version(
        root_dir,
        "3.34.8-1",
        start_menu_dirs=[start_menu_a, start_menu_b],
    )

    assert not root_dir.exists()
    assert not (start_menu_a / "QGIS LTR 3.34.8-1").exists()


def test_uninstall_version_missing_root_is_a_noop(tmp_path):
    # Ne doit pas lever si le dossier a déjà été supprimé manuellement.
    uninstall_version(tmp_path / "does-not-exist", "3.34.8-1", start_menu_dirs=[tmp_path])
