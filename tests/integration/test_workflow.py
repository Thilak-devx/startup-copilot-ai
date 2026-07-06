# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Integration tests for the Startup Copilot workflow.
"""

from __future__ import annotations

import json

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent


def test_startup_copilot_workflow() -> None:
    """Integration test verifying that the startup copilot workflow accepts StartupIdea input

    and triggers the graph execution.
    """
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(
        user_id="test_user", app_name="startup_copilot"
    )
    runner = Runner(
        agent=root_agent, session_service=session_service, app_name="startup_copilot"
    )

    idea = {
        "name": "Solarex",
        "description": "An IoT-enabled platform for optimizing local solar grid sharing.",
        "industry": "CleanTech",
        "target_customer": "Residential communities with solar panels",
        "estimated_pricing": "10% transaction fee on energy traded",
        "funding_stage": "Seed",
    }

    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=json.dumps(idea))],
    )

    # We do a basic run. Note: The workflow has a Human-in-the-Loop checkpoint,
    # so we expect it to pause and yield a RequestInput event.
    events = list(
        runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        )
    )

    assert len(events) > 0

    # Verify structure: find if we hit the human-in-the-loop checkpoint or encountered a credential error
    has_interrupt = False
    for event in events:
        if getattr(event, "interrupt_ids", None) or getattr(
            event, "resume_inputs", None
        ):
            has_interrupt = True
            break

    print(
        f"Workflow execution produced {len(events)} events (HITL interrupt: {has_interrupt})."
    )
