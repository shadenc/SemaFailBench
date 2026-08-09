from sem_fail_bench.metrics import detection_metrics, pass_rate_delta


def test_detection_metrics_and_delta():
    metrics = detection_metrics([1, 1, 0, 0], [1, 0, 0, 1])
    assert metrics["tp"] == 1
    assert metrics["fn"] == 1
    assert metrics["tn"] == 1
    assert metrics["fp"] == 1
    assert metrics["recall"] == 0.5
    assert pass_rate_delta(0.95, 0.70) == 0.25
