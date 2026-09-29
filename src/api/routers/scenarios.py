import os

from fastapi import APIRouter, HTTPException

from cross_border_ai.exceptions import CrossBorderAIError
from cross_border_ai.scenario_registry import get_scenario, list_scenarios

from ..deps import get_config
from ..schemas import ScenarioRunResponse

router = APIRouter()


@router.get("/scenarios")
def list_all() -> dict:
    return {"scenarios": list(list_scenarios().keys())}


@router.post("/scenarios/{handler}/run", response_model=ScenarioRunResponse)
def run_scenario(handler: str, body: dict | None = None) -> ScenarioRunResponse:
    cfg = get_config()
    params: dict = (body or {}).get("params", {})
    try:
        func = get_scenario(handler)
        df = func(cfg, params)
        out_dir = cfg["paths"]["output_dir"]
        files = sorted(
            [f for f in os.listdir(out_dir) if f.endswith(".csv")],
            key=lambda f: os.path.getmtime(os.path.join(out_dir, f)),
            reverse=True,
        )
        return ScenarioRunResponse(
            scenario=handler,
            status="success",
            output_file=files[0] if files else None,
            message=f"{len(df)} rows processed",
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except CrossBorderAIError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e