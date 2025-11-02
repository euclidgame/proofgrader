from .single import run_workflow as single
from .decompose_then_judge import run_workflow as decompose_then_judge
from .repeat_and_aggregate import run_workflow as repeat_and_aggregate
from .reflect_and_revise import run_workflow as reflect_and_revise

WORKFLOWS = {
    "single": single,
    "decompose-then-judge": decompose_then_judge,
    "repeat-and-aggregate": repeat_and_aggregate,
    "reflect-and-revise": reflect_and_revise,
}


