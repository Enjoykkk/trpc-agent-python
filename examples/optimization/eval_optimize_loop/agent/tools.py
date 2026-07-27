"""Deterministic tools used by the order-support example."""

from __future__ import annotations


ORDERS = {
    "A100": {"status": "shipped", "amount": 299, "refundable": True},
    "A200": {"status": "completed", "amount": 599, "refundable": False},
}


async def get_order(order_id: str) -> dict:
    """Return a stable structured result without correcting invalid order IDs."""
    order = ORDERS.get(order_id)
    if order is None:
        return {"found": False, "order_id": order_id, "error": "order_not_found"}
    return {"found": True, "order_id": order_id, **order}


async def search_refund_policy(question: str) -> dict:
    """Return deterministic refund-policy facts for evaluation."""
    return {
        "question": question,
        "shipped_order": "已发货订单需以退货政策审核结果为准，不能直接承诺退款。",
        "completed_order": "已完成订单不支持无条件退款，需按售后政策审核。",
    }
