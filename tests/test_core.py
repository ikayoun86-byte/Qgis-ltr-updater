from qgis_ltr_updater import core
from qgis_ltr_updater.installed import InstallRecord


def test_build_plan_no_update_needed(monkeypatch):
    records = [InstallRecord(version="3.40.5-1", root="r1", installed_at="")]
    monkeypatch.setattr(core, "get_latest_ltr_version", lambda: "3.40.5-1")

    plan = core.build_plan(records=records)

    assert plan.needs_update is False
    assert plan.current == "3.40.5-1"
    assert plan.a_retirer == []


def test_build_plan_flags_update_and_excess(monkeypatch):
    records = [
        InstallRecord(version="3.28.0-1", root="r0", installed_at=""),
        InstallRecord(version="3.34.8-1", root="r1", installed_at=""),
    ]
    monkeypatch.setattr(core, "get_latest_ltr_version", lambda: "3.40.5-1")

    plan = core.build_plan(records=records)

    assert plan.needs_update is True
    assert plan.current == "3.34.8-1"
    assert plan.previous == "3.28.0-1"
    # 2 versions connues + la nouvelle = 3, on ne garde que 2 (KEEP_VERSIONS) :
    # la plus ancienne (3.28.0-1) doit être proposée au retrait.
    assert [r.version for r in plan.a_retirer] == ["3.28.0-1"]


def test_build_plan_within_retention_no_excess(monkeypatch):
    records = [InstallRecord(version="3.34.8-1", root="r1", installed_at="")]
    monkeypatch.setattr(core, "get_latest_ltr_version", lambda: "3.40.5-1")

    plan = core.build_plan(records=records)

    assert plan.a_retirer == []
