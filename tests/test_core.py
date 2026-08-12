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


def test_build_plan_empty_records_resolves_bootstrap(monkeypatch):
    monkeypatch.setattr(core, "get_latest_ltr_version", lambda: "3.40.10-1")
    monkeypatch.setattr(
        core,
        "get_ltr_series",
        lambda limit=None: [
            {"version": "3.40.10", "published_at": "2026-01-08T00:00:00Z"},
            {"version": "3.34.15", "published_at": "2025-08-06T00:00:00Z"},
        ],
    )
    monkeypatch.setattr(
        core,
        "find_snapshot_for_version",
        lambda target, not_before=None, not_after=None: ("https://.../snapshots/2025-08-15", "3.34.15-1"),
    )

    plan = core.build_plan(records=[])

    assert plan.bootstrap == {"version": "3.34.15-1", "site": "https://.../snapshots/2025-08-15"}


def test_build_plan_empty_records_bootstrap_none_when_unresolved(monkeypatch):
    monkeypatch.setattr(core, "get_latest_ltr_version", lambda: "3.40.10-1")
    monkeypatch.setattr(
        core,
        "get_ltr_series",
        lambda limit=None: [
            {"version": "3.40.10", "published_at": "2026-01-08T00:00:00Z"},
            {"version": "3.34.15", "published_at": "2025-08-06T00:00:00Z"},
        ],
    )
    monkeypatch.setattr(
        core, "find_snapshot_for_version", lambda target, not_before=None, not_after=None: (None, None)
    )

    plan = core.build_plan(records=[])

    assert plan.bootstrap is None


def test_build_plan_empty_records_bootstrap_none_on_error(monkeypatch):
    # Toute erreur pendant la résolution (réseau, format inattendu, ...) ne
    # doit jamais faire planter build_plan : dégradation vers bootstrap=None.
    monkeypatch.setattr(core, "get_latest_ltr_version", lambda: "3.40.10-1")

    def boom(limit=None):
        raise RuntimeError("panne réseau simulée")

    monkeypatch.setattr(core, "get_ltr_series", boom)

    plan = core.build_plan(records=[])

    assert plan.bootstrap is None


def test_build_plan_nonempty_records_never_bootstraps(monkeypatch):
    monkeypatch.setattr(core, "get_latest_ltr_version", lambda: "3.40.10-1")

    def should_not_be_called(*args, **kwargs):
        raise AssertionError("get_ltr_series ne doit pas être appelé si des versions sont déjà installées")

    monkeypatch.setattr(core, "get_ltr_series", should_not_be_called)

    records = [InstallRecord(version="3.40.10-1", root="r1", installed_at="")]
    plan = core.build_plan(records=records)

    assert plan.bootstrap is None


def test_perform_install_with_bootstrap_installs_previous_first(monkeypatch):
    calls = []

    bootstrap_record = InstallRecord(version="3.34.15-1", root="rprev", installed_at="")
    refreshed_plan = core.Plan(
        records=[bootstrap_record], latest="3.40.10-1", current="3.34.15-1",
        previous=None, needs_update=True, a_retirer=[], bootstrap=None,
    )
    final_record = InstallRecord(version="3.40.10-1", root="rlatest", installed_at="")

    def fake_install_specific_version(version, site=None, log=print):
        calls.append(("install_specific_version", version, site))
        return bootstrap_record

    def fake_save_state(records):
        calls.append(("save_state", list(records)))

    def fake_build_plan():
        calls.append(("build_plan",))
        return refreshed_plan

    def fake_perform_install(plan, log=print):
        calls.append(("perform_install", plan))
        return final_record

    monkeypatch.setattr(core, "install_specific_version", fake_install_specific_version)
    monkeypatch.setattr(core, "save_state", fake_save_state)
    monkeypatch.setattr(core, "build_plan", fake_build_plan)
    monkeypatch.setattr(core, "perform_install", fake_perform_install)

    initial_plan = core.Plan(
        records=[], latest="3.40.10-1", current=None, previous=None, needs_update=True,
        a_retirer=[], bootstrap={"version": "3.34.15-1", "site": "https://.../snapshots/2025-08-15"},
    )

    result = core.perform_install_with_bootstrap(initial_plan)

    assert result is final_record
    assert calls == [
        ("install_specific_version", "3.34.15-1", "https://.../snapshots/2025-08-15"),
        ("save_state", [bootstrap_record]),
        ("build_plan",),
        ("perform_install", refreshed_plan),
    ]


def test_perform_install_with_bootstrap_skips_when_none(monkeypatch):
    calls = []
    final_record = InstallRecord(version="3.40.10-1", root="rlatest", installed_at="")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("le bootstrap ne doit pas se déclencher quand plan.bootstrap est None")

    def fake_perform_install(plan, log=print):
        calls.append(plan)
        return final_record

    monkeypatch.setattr(core, "install_specific_version", fail_if_called)
    monkeypatch.setattr(core, "save_state", fail_if_called)
    monkeypatch.setattr(core, "perform_install", fake_perform_install)

    plan = core.Plan(
        records=[InstallRecord(version="3.34.8-1", root="r1", installed_at="")],
        latest="3.40.10-1", current="3.34.8-1", previous=None,
        needs_update=True, a_retirer=[], bootstrap=None,
    )

    result = core.perform_install_with_bootstrap(plan)

    assert result is final_record
    assert calls == [plan]
