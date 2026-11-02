from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Iterator, Mapping
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class TraceContext:
    execution_id: str
    parent_step_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    application: str | None = None
    workflow: str | None = None
    agent_name: str | None = None
    feature: str | None = None
    plan_key: str | None = None
    credits: Decimal | float | int | None = None
    customer_id: str | None = None
    conversation_id: str | None = None
    user_id: str | None = None
    prompt_id: str | None = None
    prompt_version: str | None = None
    revenue_usd: Decimal | float | None = None

    def attributes(self) -> dict[str, Any]:
        attributes = dict(self.metadata)
        attributes.update({
            key: value
            for key, value in {
                "application": self.application,
                "workflow": self.workflow,
                "agent_name": self.agent_name,
                "feature": self.feature,
                "plan_key": self.plan_key,
                "credits": float(self.credits) if self.credits is not None else None,
                "customer_id": self.customer_id,
                "conversation_id": self.conversation_id,
                "user_id": self.user_id,
                "prompt_id": self.prompt_id,
                "prompt_version": self.prompt_version,
                "revenue_usd": float(self.revenue_usd) if self.revenue_usd is not None else None,
            }.items()
            if value is not None
        })
        return attributes


_current_trace: ContextVar[TraceContext | None] = ContextVar(
    "ganivra_trace", default=None
)


def current_trace() -> TraceContext | None:
    return _current_trace.get()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


@contextmanager
def trace(
    *,
    metadata: Mapping[str, Any] | None = None,
    application: str | None = None,
    workflow: str | None = None,
    agent_name: str | None = None,
    feature: str | None = None,
    plan_key: str | None = None,
    credits: Decimal | float | int | None = None,
    customer_id: str | None = None,
    conversation_id: str | None = None,
    user_id: str | None = None,
    prompt_id: str | None = None,
    prompt_version: str | None = None,
    revenue_usd: Decimal | float | None = None,
    execution_id: str | None = None,
    parent_step_id: str | None = None,
) -> Iterator[TraceContext]:
    parent = current_trace()
    merged_metadata = dict(getattr(parent, "metadata", {}))
    if metadata is not None:
        merged_metadata.update(metadata)
    context = TraceContext(
        execution_id=execution_id or new_id("exec"),
        parent_step_id=(
            parent_step_id
            if parent_step_id is not None
            else getattr(parent, "parent_step_id", None)
        ),
        metadata=merged_metadata,
        application=(
            application
            if application is not None
            else getattr(parent, "application", None)
        ),
        workflow=workflow if workflow is not None else getattr(parent, "workflow", None),
        agent_name=agent_name if agent_name is not None else getattr(parent, "agent_name", None),
        feature=feature if feature is not None else getattr(parent, "feature", None),
        plan_key=plan_key if plan_key is not None else getattr(parent, "plan_key", None),
        credits=credits if credits is not None else getattr(parent, "credits", None),
        customer_id=(
            customer_id
            if customer_id is not None
            else getattr(parent, "customer_id", None)
        ),
        conversation_id=(
            conversation_id
            if conversation_id is not None
            else getattr(parent, "conversation_id", None)
        ),
        user_id=user_id if user_id is not None else getattr(parent, "user_id", None),
        prompt_id=(
            prompt_id if prompt_id is not None else getattr(parent, "prompt_id", None)
        ),
        prompt_version=(
            prompt_version
            if prompt_version is not None
            else getattr(parent, "prompt_version", None)
        ),
        revenue_usd=(
            revenue_usd
            if revenue_usd is not None
            else getattr(parent, "revenue_usd", None)
        ),
    )
    token = _current_trace.set(context)
    try:
        yield context
    finally:
        _current_trace.reset(token)
