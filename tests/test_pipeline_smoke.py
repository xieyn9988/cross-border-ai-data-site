from cross_border_ai.pipeline import run_pipeline


def test_pipeline_all_success(cfg):
    results = run_pipeline(cfg)
    assert all(v == "success" for v in results.values()), results