from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from config import MODEL


ORCHESTRATOR_INSTRUCTIONS = """
You are CampaignLab's Evidence Orchestrator, a marketing decision-science planner.

Operating rules:
1. Use registered tools whenever a claim depends on deterministic computation or the uploaded dataset.
2. For uploaded data, call inspect_dataset_intelligence before recommending an analysis.
3. Then call rank_candidate_methods before naming a preferred analytical method.
4. Call recommend_decision_visualizations when explaining how the evidence should be visualized.
5. Never calculate p-values, confidence intervals, sample sizes, lift, power, dataset statistics, or marketing metrics yourself when a matching tool exists.
6. Never say an analysis was executed unless a deterministic tool actually executed it. If a Live method is structurally eligible and the user asked a question that method can directly answer, execute the method rather than stopping at a plan. If one required argument cannot be inferred safely (for example intervention date, control arm, or target), ask for that specific input instead of guessing.
7. Distinguish candidate methods, structurally eligible methods, executable methods, and methods that are merely Planned/Research.
8. Passing a schema/data gate never establishes causality. Identification and method-specific assumptions still matter.
9. Prefer one recommended method plus at most two serious alternatives. Explain why the winner fits better.
10. If the question cannot be answered with the available evidence, say so and name the smallest additional evidence needed.
11. Use simple marketing-executive language. Explain technical terms under 'What this means'.
12. Do not request raw rows in tool arguments. Dataset tools already operate on the server-side DataFrame.
13. Do not generate or execute arbitrary Python or SQL. Analyst handoff code may be described only after the analytical specification is clear.
14. Do not generate chart ideas from imagination when the visualization tool can recommend them.
15. Be decisive without manufacturing certainty.

Your final response must distinguish planning from conclusion. If no deterministic analysis was executed, title the first section 'CampaignLab's Plan'. If a deterministic analysis was executed and supports a business conclusion, title it 'CampaignLab's Call'. Never label a plan as a call.

Your final response should be concise and structured around:
- CampaignLab's Plan OR CampaignLab's Call, using the rule above
- What was actually executed (or why execution was blocked)
- Why this method / what the tools found
- What this means
- Analysis risks or missing evidence
- Recommended visuals
- Next action
""".strip()


@dataclass
class ToolTrace:
    name: str
    arguments: dict[str, Any]
    status: str
    output_summary: str


@dataclass
class OrchestrationResult:
    text: str
    traces: list[ToolTrace]
    usage: dict[str, int]
    response_id: str | None


def _usage_dict(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    return {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }


def _summarize_output(output: dict[str, Any], max_chars: int = 320) -> str:
    text = json.dumps(output, ensure_ascii=False, default=str, separators=(",", ":"))
    return text if len(text) <= max_chars else text[: max_chars - 3] + "..."


def run_evidence_orchestrator(
    client: Any,
    user_message: str,
    runtime: Any,
    *,
    max_rounds: int = 6,
    max_total_tool_calls: int = 12,
) -> OrchestrationResult:
    """Bounded Responses API function-calling loop over whitelisted local tools."""
    if not user_message.strip():
        raise ValueError("Evidence question cannot be empty.")

    tools = runtime.tool_specs()
    traces: list[ToolTrace] = []
    total_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    initial_message = user_message
    if getattr(runtime, "dataframe", None) is not None:
        initial_message = (
            "A dataset is loaded server-side. First inspect it with inspect_dataset_intelligence. "
            "Then rank methods with rank_candidate_methods. Use recommend_decision_visualizations before proposing charts. "
            "Check implementation status before claiming CampaignLab can execute a method.\n\n" + user_message
        )

    response = client.responses.create(
        model=MODEL,
        instructions=ORCHESTRATOR_INSTRUCTIONS,
        input=initial_message,
        tools=tools,
        tool_choice="required",
    )

    for _round in range(max_rounds):
        usage = _usage_dict(response)
        for key in total_usage:
            total_usage[key] += usage[key]

        calls = [item for item in getattr(response, "output", []) if getattr(item, "type", None) == "function_call"]
        if not calls:
            return OrchestrationResult(
                text=getattr(response, "output_text", "") or "CampaignLab completed the analysis but returned no text.",
                traces=traces,
                usage=total_usage,
                response_id=getattr(response, "id", None),
            )

        if len(traces) + len(calls) > max_total_tool_calls:
            raise RuntimeError("CampaignLab stopped the tool loop because it exceeded the safety limit on tool calls.")

        outputs = []
        for call in calls:
            name = str(getattr(call, "name", ""))
            raw_arguments = getattr(call, "arguments", "{}") or "{}"
            try:
                arguments = json.loads(raw_arguments)
                if not isinstance(arguments, dict):
                    raise ValueError("Tool arguments must be a JSON object.")
                tool_output = runtime.execute(name, arguments)
                status = "ok"
            except Exception as exc:
                arguments = {}
                try:
                    parsed = json.loads(raw_arguments)
                    if isinstance(parsed, dict):
                        arguments = parsed
                except Exception:
                    pass
                tool_output = {"error": str(exc), "tool": name}
                status = "error"

            traces.append(ToolTrace(name=name, arguments=arguments, status=status, output_summary=_summarize_output(tool_output)))
            outputs.append({
                "type": "function_call_output",
                "call_id": getattr(call, "call_id"),
                "output": json.dumps(tool_output, ensure_ascii=False, default=str),
            })

        response = client.responses.create(
            model=MODEL,
            instructions=ORCHESTRATOR_INSTRUCTIONS,
            previous_response_id=getattr(response, "id"),
            input=outputs,
            tools=tools,
            tool_choice="auto",
        )

    raise RuntimeError("CampaignLab stopped because the evidence tool loop did not converge within the configured number of rounds.")
