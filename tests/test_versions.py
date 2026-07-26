from qgis_ltr_updater.versions import is_newer, sort_key


def test_sort_key_orders_patch_releases():
    assert sort_key("3.40.5-1") > sort_key("3.34.8-1")


def test_sort_key_orders_by_build_number():
    assert sort_key("3.40.5-2") > sort_key("3.40.5-1")


def test_is_newer_true_for_newer_series():
    assert is_newer("3.44.0-1", "3.40.5-1") is True


def test_is_newer_false_for_same_version():
    assert is_newer("3.40.5-1", "3.40.5-1") is False


def test_is_newer_false_for_older_version():
    assert is_newer("3.34.8-1", "3.40.5-1") is False
