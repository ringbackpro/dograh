from unittest.mock import AsyncMock, Mock

import pytest
from pipecat.frames.frames import BotStartedSpeakingFrame, UserStartedSpeakingFrame
from pipecat.processors.aggregators.llm_context import LLMContext

from api.services.workflow.dto import (
    AgentNodeData,
    EdgeDataDTO,
    EndCallNodeData,
    Position,
    ReactFlowDTO,
    RFEdgeDTO,
    RFNodeDTO,
    StartCallNodeData,
)
from api.services.workflow.pipecat_engine import PipecatEngine
from api.services.workflow.pipecat_engine_context_composer import (
    compose_functions_for_node,
)
from api.services.workflow.workflow_graph import WorkflowGraph


def _node(id_: str, type_: str, data):
    return RFNodeDTO(id=id_, type=type_, position=Position(x=0, y=0), data=data)


def _start_node(greeting: str | None = "Hello."):
    return _node(
        "start",
        "startCall",
        StartCallNodeData(
            name="Start",
            prompt="Start prompt",
            is_start=True,
            allow_interrupt=True,
            add_global_prompt=False,
            greeting=greeting,
            greeting_type="text" if greeting else None,
            extraction_enabled=False,
        ),
    )


def _agent_node(id_: str = "agent", name: str = "Agent"):
    return _node(
        id_,
        "agentNode",
        AgentNodeData(
            name=name,
            prompt=f"{name} prompt",
            allow_interrupt=True,
            add_global_prompt=False,
            extraction_enabled=False,
        ),
    )


def _end_node():
    return _node(
        "end",
        "endCall",
        EndCallNodeData(
            name="End",
            prompt="End prompt",
            is_end=True,
            allow_interrupt=False,
            add_global_prompt=False,
            extraction_enabled=False,
        ),
    )


def _edge(
    id_: str,
    source: str,
    target: str,
    *,
    label: str,
    condition: str,
    transition_mode: str = "llm",
):
    return RFEdgeDTO(
        id=id_,
        source=source,
        target=target,
        data=EdgeDataDTO(
            label=label,
            condition=condition,
            transition_mode=transition_mode,
        ),
    )


def _workflow(edges: list[RFEdgeDTO], extra_nodes: list[RFNodeDTO] | None = None):
    return WorkflowGraph(
        ReactFlowDTO(
            nodes=[_start_node(), _agent_node(), _end_node()] + (extra_nodes or []),
            edges=edges,
        )
    )


def _engine(workflow: WorkflowGraph):
    llm = Mock()
    llm._update_settings = AsyncMock()
    llm.queue_frame = AsyncMock()
    llm.register_function = Mock()
    task = Mock()
    task.queue_frame = AsyncMock()
    engine = PipecatEngine(
        llm=llm,
        context=LLMContext(),
        workflow=workflow,
        call_context_vars={},
        workflow_run_id=1,
    )
    engine.set_task(task)
    engine._perform_variable_extraction_if_needed = AsyncMock()
    return engine, llm, task


@pytest.mark.asyncio
async def test_auto_transition_advances_after_greeting_without_user_input():
    workflow = _workflow(
        [
            _edge(
                "start-agent",
                "start",
                "agent",
                label="Continue",
                condition="After greeting",
                transition_mode="auto",
            )
        ]
    )
    engine, llm, _task = _engine(workflow)

    await engine.set_node("start")
    await engine.queue_node_opening(node_id="start", previous_node_id=None)
    await engine.handle_bot_stopped_speaking()

    assert engine._current_node.id == "agent"
    assert engine.skip_edge_triggered_count == 1
    assert llm.queue_frame.await_count == 1
    assert any(
        "Workflow auto-transition executed" in msg["content"]
        for msg in engine.context.messages
        if msg["role"] == "system"
    )


@pytest.mark.asyncio
async def test_auto_edge_is_not_exposed_as_llm_tool():
    workflow = _workflow(
        [
            _edge(
                "start-agent",
                "start",
                "agent",
                label="Auto Continue",
                condition="After greeting",
                transition_mode="auto",
            ),
            _edge(
                "start-end",
                "start",
                "end",
                label="End Call",
                condition="When the user asks to end",
            ),
        ]
    )
    engine, llm, _task = _engine(workflow)
    start = workflow.nodes["start"]

    functions = await compose_functions_for_node(
        node=start,
        custom_tool_manager=None,
    )
    await engine.set_node("start")

    assert [f.name for f in functions] == ["end_call"]
    assert "auto_continue" not in [call.args[0] for call in llm.register_function.call_args_list]
    assert "end_call" in [call.args[0] for call in llm.register_function.call_args_list]
    assert workflow.warnings


def test_multiple_auto_edges_from_one_node_are_rejected():
    with pytest.raises(ValueError) as exc_info:
        _workflow(
            [
                _edge(
                    "start-agent",
                    "start",
                    "agent",
                    label="Auto One",
                    condition="First auto",
                    transition_mode="auto",
                ),
                _edge(
                    "start-end",
                    "start",
                    "end",
                    label="Auto Two",
                    condition="Second auto",
                    transition_mode="auto",
                ),
            ]
        )

    messages = [err["message"] for err in exc_info.value.args[0]]
    assert "A node can have at most one auto transition edge" in messages


@pytest.mark.asyncio
async def test_default_llm_transition_behavior_is_unchanged():
    workflow = _workflow(
        [
            _edge(
                "start-end",
                "start",
                "end",
                label="End Call",
                condition="When the user asks to end",
            )
        ]
    )
    engine, llm, _task = _engine(workflow)
    start = workflow.nodes["start"]

    functions = await compose_functions_for_node(
        node=start,
        custom_tool_manager=None,
    )
    await engine.set_node("start")

    assert [f.name for f in functions] == ["end_call"]
    llm.register_function.assert_called_once()
    assert llm.register_function.call_args.args[0] == "end_call"


@pytest.mark.asyncio
async def test_duplicate_bot_stopped_frame_does_not_repeat_auto_transition():
    workflow = _workflow(
        [
            _edge(
                "start-agent",
                "start",
                "agent",
                label="Continue",
                condition="After greeting",
                transition_mode="auto",
            )
        ]
    )
    engine, _llm, _task = _engine(workflow)
    engine._transition_via_edge = AsyncMock()

    await engine.set_node("start")
    await engine.queue_node_opening(node_id="start", previous_node_id=None)
    await engine.handle_bot_stopped_speaking()
    await engine.handle_bot_stopped_speaking()

    engine._transition_via_edge.assert_awaited_once()
    assert engine.skip_edge_triggered_count == 1
    assert engine.duplicate_transition_prevented == 1


@pytest.mark.asyncio
async def test_user_interruption_aborts_auto_transition():
    workflow = _workflow(
        [
            _edge(
                "start-agent",
                "start",
                "agent",
                label="Continue",
                condition="After greeting",
                transition_mode="auto",
            )
        ]
    )
    engine, _llm, _task = _engine(workflow)

    await engine.set_node("start")
    await engine.queue_node_opening(node_id="start", previous_node_id=None)
    await engine.should_mute_user(BotStartedSpeakingFrame())
    await engine.should_mute_user(UserStartedSpeakingFrame())
    await engine.handle_bot_stopped_speaking()

    assert engine._current_node.id == "start"
    assert engine.skip_edge_interrupt_aborts == 1
    assert engine.skip_edge_triggered_count == 0


@pytest.mark.asyncio
async def test_suppression_blocks_auto_transition_until_opening_is_armed():
    workflow = _workflow(
        [
            _edge(
                "start-agent",
                "start",
                "agent",
                label="Continue",
                condition="After greeting",
                transition_mode="auto",
            )
        ]
    )
    engine, _llm, _task = _engine(workflow)
    engine._transition_via_edge = AsyncMock()

    await engine.set_node("start")
    await engine.handle_bot_stopped_speaking()

    engine._transition_via_edge.assert_not_awaited()
    assert engine.suppress_skip_until_node_opening_complete is True
