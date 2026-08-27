from vbagent.authoring import worker
from vbagent.authoring.application import AuthoringApplication, AuthoringIntent
from vbagent.authoring.store import AuthoringStore


def test_worker_records_dispatch_completion_without_protocol_output(tmp_path, monkeypatch):
    planned = AuthoringApplication(tmp_path).plan(
        AuthoringIntent(
            exam="jee_main",
            subject="physics",
            chapter="kinematics",
            topics=["projectile motion"],
            count=1,
        )
    )
    token = "dispatch-success"
    with AuthoringStore(tmp_path) as store:
        assert store.reserve_dispatch(planned.run_id, token, resume=False)

    monkeypatch.setattr(
        worker.AuthoringRunService,
        "execute",
        lambda self, run_id, concurrency=None: {"run_id": run_id, "pending": 1},
    )

    exit_code = worker.main(
        [
            "--output",
            str(tmp_path),
            "--run-id",
            planned.run_id,
            "--dispatch-token",
            token,
        ]
    )

    assert exit_code == 0
    with AuthoringStore(tmp_path) as store:
        dispatch = store.get_dispatch(planned.run_id)
    assert dispatch["status"] == "finished"
    assert dispatch["finished_at"]


def test_worker_records_dispatch_failure(tmp_path, monkeypatch):
    planned = AuthoringApplication(tmp_path).plan(
        AuthoringIntent(
            exam="jee_main",
            subject="physics",
            chapter="kinematics",
            topics=["projectile motion"],
            count=1,
        )
    )
    token = "dispatch-failure"
    with AuthoringStore(tmp_path) as store:
        assert store.reserve_dispatch(planned.run_id, token, resume=False)

    def fail(*_args, **_kwargs):
        raise RuntimeError("worker infrastructure failed")

    monkeypatch.setattr(worker.AuthoringRunService, "execute", fail)

    exit_code = worker.main(
        [
            "--output",
            str(tmp_path),
            "--run-id",
            planned.run_id,
            "--dispatch-token",
            token,
        ]
    )

    assert exit_code == 1
    with AuthoringStore(tmp_path) as store:
        dispatch = store.get_dispatch(planned.run_id)
    assert dispatch["status"] == "failed"
    assert "worker infrastructure failed" in dispatch["error_message"]
