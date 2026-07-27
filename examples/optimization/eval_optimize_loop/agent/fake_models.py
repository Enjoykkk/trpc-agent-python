"""Deterministic offline behavior driven by prompt directives.

The fake executor deliberately reads the same prompt files as the agent.  It is
not a score fixture: changing a directive changes its reply and tool trace.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .tools import get_order, search_refund_policy


@dataclass
class FakeResult:
    response: str
    tool_calls: list[dict]


def _setting(prompt: str, name: str, default: str) -> str:
    match = re.search(rf"{re.escape(name)}\s*=\s*([\w_]+)", prompt)
    return match.group(1) if match else default


async def invoke_fake_agent(query: str, prompt: str) -> FakeResult:
    """Execute deterministic tool/reply behavior derived from candidate prompt text."""
    strict_id = _setting(prompt, "order_id_mode", "guess_when_missing") == "strict"
    require_policy = _setting(prompt, "refund_policy_mode", "optional") == "required"
    strict_json = _setting(prompt, "json_output_mode", "prose") == "strict_json"
    order_match = re.search(r"\bA\d{3}\b", query)
    order_id = order_match.group(0) if order_match else None
    tools: list[dict] = []
    if not order_id and strict_id and "退款" not in query:
        return FakeResult("请提供订单号，我不能猜测订单信息。", tools)
    if not order_id:
        order_id = "A100"
    if "订单" in query:
        order = await get_order(order_id); tools.append({"name": "get_order", "args": {"order_id": order_id}})
    else:
        order = None
    if "退款" in query and (require_policy or "已发货" in query):
        policy = await search_refund_policy(query); tools.append({"name": "search_refund_policy", "args": {"question": query}})
        if order and order.get("status") == "completed":
            return FakeResult(policy["completed_order"], tools)
        return FakeResult(policy["shipped_order"], tools)
    if order and "JSON" in query.upper():
        if strict_json:
            return FakeResult(json.dumps({"order_id": order_id, "status": order["status"]}, ensure_ascii=False), tools)
        return FakeResult(f"订单号：{order_id}，状态：{order['status']}", tools)
    if order:
        status = {"shipped": "已发货", "completed": "已完成"}[order["status"]]
        return FakeResult(f"订单 {order_id} {status}", tools)
    return FakeResult("请说明需要查询的订单信息。", tools)
