"""
AI Orchestration Core — the primary process of Chitra.

Boots on startup, never exits. Handles:
1. Input handling — receives user text from Voice I/O
2. Context assembly — assembles Memory + System State + history before every LLM call
3. LLM reasoning — sends context to local LLM, parses structured JSON response
4. Action execution — dispatches to capability modules based on LLM decisions
5. Memory storage — stores new memory entries from every LLM response

Also starts the proactive background loop.
"""

import asyncio
import inspect
import logging
import os

from capabilities.calendar import Calendar
from capabilities.contacts import Contacts
from capabilities.memory import Memory
from capabilities.reminders import Reminders
from capabilities.system_state import SystemState
from capabilities.tasks import Tasks
from capabilities.voice_io import VoiceIO
from llm.client import LLMClient
from orchestration.context import ContextAssembler

logger = logging.getLogger(__name__)


class OrchestrationCore:
    """Primary Chitra process. Orchestrates all capabilities through the LLM."""

    def __init__(self):
        self.is_user_active = False
        self.conversation_history: list[dict] = []
        self.max_history_turns = int(os.environ.get("CHITRA_HISTORY_TURNS", "10"))

        # Data directory — all capability databases live here
        self.data_dir = os.environ.get(
            "CHITRA_DATA_DIR", os.path.expanduser("~/.chitra/data"),
        )
        os.makedirs(self.data_dir, exist_ok=True)

        # Initialize capabilities
        self.memory = Memory(os.path.join(self.data_dir, "memory.db"))
        self.system_state = SystemState()
        self.contacts = Contacts(os.path.join(self.data_dir, "contacts.db"))
        self.calendar = Calendar(os.path.join(self.data_dir, "calendar.db"))
        self.reminders = Reminders(os.path.join(self.data_dir, "reminders.db"))
        self.tasks = Tasks(os.path.join(self.data_dir, "tasks.db"))
        self.voice_io = VoiceIO()

        # LLM client and context assembler
        self.llm = LLMClient()
        self.context_assembler = ContextAssembler(
            memory=self.memory,
            system_state=self.system_state,
            calendar=self.calendar,
            reminders=self.reminders,
        )

        # Capability dispatch table — maps capability names to instances
        self._capabilities = {
            "contacts": self.contacts,
            "calendar": self.calendar,
            "reminders": self.reminders,
            "tasks": self.tasks,
            "memory": self.memory,
            "voice_io": self.voice_io,
        }

        # Proactive loop task reference — for clean shutdown
        self._proactive_task: asyncio.Task | None = None

        logger.info("Orchestration Core initialized — data_dir: %s", self.data_dir)

    async def run(self):
        """Main entry point. Initialize capabilities, run onboarding if needed, start loops.

        This method never returns under normal operation — it runs the
        conversation loop forever until the process is terminated.
        """
        try:
            logger.info("Chitra booting...")

            # Set input mode from environment if configured
            input_mode = os.environ.get("CHITRA_INPUT_MODE", "text")
            mode_result = await self.voice_io.set_input_mode(input_mode)
            if "error" in mode_result:
                logger.warning(
                    "Could not set input mode to '%s': %s — falling back to text",
                    input_mode,
                    mode_result["error"],
                )
                await self.voice_io.set_input_mode("text")

            # Check and run onboarding if this is the first boot
            from onboarding.flow import OnboardingFlow

            onboarding = OnboardingFlow(self)
            if await onboarding.should_run():
                logger.info("First run detected — starting onboarding")
                await onboarding.run()
                logger.info("Onboarding complete")

            # Start the proactive background loop
            from orchestration.proactive import ProactiveLoop

            proactive = ProactiveLoop(self)
            self._proactive_task = asyncio.create_task(proactive.run())
            logger.info("Proactive loop started")

            # Run the main conversation loop
            logger.info("Chitra is ready. Starting conversation loop.")
            await self._conversation_loop()

        except KeyboardInterrupt:
            logger.info("Shutdown requested by user")
        except Exception as e:
            logger.error("Fatal error in Orchestration Core: %s", e)
        finally:
            await self._shutdown()

    async def _conversation_loop(self):
        """Main conversation loop — listen, think, respond, repeat.

        This is the core interaction cycle:
        1. Listen for user input via Voice I/O
        2. Assemble full context (Memory, System State, Calendar, Reminders, history)
        3. Send to LLM for reasoning
        4. If action returned — execute it, then make a second LLM call with the result
        5. Store any new memory entries
        6. Display and speak the response
        7. Repeat
        """
        while True:
            try:
                # Mark user as active during conversation handling
                self.is_user_active = True

                # 1. Listen for input
                listen_result = await self.voice_io.listen()

                if "error" in listen_result:
                    logger.error("Listen error: %s", listen_result["error"])
                    continue

                user_text = listen_result.get("text", "").strip()
                if not user_text:
                    self.is_user_active = False
                    continue

                # 2. Process the input through the full pipeline
                response_text = await self.handle_input(user_text)

                # 3. Display and speak the response
                await self.voice_io.display(user_text, response_text)
                await self.voice_io.speak(response_text)

                self.is_user_active = False

            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.error("Conversation loop error: %s", e)
                self.is_user_active = False
                # Don't crash — log and continue
                await self.voice_io.display(
                    "", "I'm sorry, something went wrong. Let me try again.",
                )

    async def handle_input(self, user_text: str) -> str:
        """Process user input through the full pipeline: context → LLM → action → response.

        This is the main reasoning pipeline, also used by the proactive loop
        when it needs to formulate a response with action support.

        Args:
            user_text: the user's input text (from text or voice mode)

        Returns:
            The conversational response text from Chitra

        """
        try:
            # Assemble context — Memory, System State, Calendar, Reminders
            context = await self.context_assembler.assemble(self.conversation_history)
            system_prompt = context["system_prompt"]

            # First LLM call — understand intent and decide action
            llm_response = await self.llm.call(
                system_prompt, user_text, self.conversation_history,
            )

            response_text = llm_response.get("response", "")
            action = llm_response.get("action")
            memory_entries = llm_response.get("memory_store", [])

            # Execute action if the LLM decided one is needed
            if action is not None:
                action_result = await self.execute_action(action)

                if action_result is not None:
                    # Second LLM call — incorporate action result into response
                    followup_message = (
                        f"The action was executed. Here is the result:\n"
                        f"{action_result}\n\n"
                        f"Now formulate a natural conversational response to the user "
                        f"incorporating this result. The user's original request was: "
                        f"{user_text}"
                    )

                    followup_response = await self.llm.call(
                        system_prompt, followup_message, self.conversation_history,
                    )
                    response_text = followup_response.get("response", response_text)

                    # Collect any additional memory entries from the followup
                    followup_memories = followup_response.get("memory_store", [])
                    memory_entries.extend(followup_memories)

            # Store any new memory entries immediately
            if memory_entries:
                await self.store_memories(memory_entries)

            # Update conversation history
            self._update_history(user_text, response_text)

            return response_text

        except Exception as e:
            logger.error("Handle input failed: %s", e)
            return "I'm sorry, I had trouble processing that. Could you try again?"

    async def execute_action(self, action: dict) -> dict | None:
        """Dispatch an action to the appropriate capability module.

        The LLM returns actions in this format:
            {
                "capability": "contacts",
                "action": "get",
                "params": {"name": "Ravi"}
            }

        This method maps that to the correct capability instance and calls the
        appropriate async method with the given parameters.

        Returns:
            The capability's result dict, or None if the action could not be executed.

        """
        try:
            capability_name = action.get("capability")
            action_name = action.get("action")
            params = action.get("params", {})

            if not capability_name or not action_name:
                logger.warning("Action missing capability or action name: %s", action)
                return None

            # Look up capability instance
            capability = self._capabilities.get(capability_name)
            if capability is None:
                logger.warning("Unknown capability: %s", capability_name)
                return None

            # Look up the method on the capability
            method = getattr(capability, action_name, None)
            if method is None or not callable(method):
                logger.warning(
                    "Unknown action '%s' on capability '%s'",
                    action_name,
                    capability_name,
                )
                return None

            # Call the method with params
            # Some actions take a single dict param (create, update),
            # some take keyword args (get, list, complete, etc.)
            if params and isinstance(params, dict):
                # Detect whether the method expects a single dict argument
                # (like create(task), create(contact)) or keyword args
                sig = inspect.signature(method)
                param_names = [
                    p.name
                    for p in sig.parameters.values()
                    if p.name != "self"
                ]

                if len(param_names) == 1 and param_names[0] in (
                    "task",
                    "contact",
                    "event",
                    "reminder",
                    "entry",
                ):
                    # Single-dict methods: create(task), create(contact), etc.
                    result = await method(params)
                else:
                    # Keyword-argument methods: get(name=...), list(status=...), etc.
                    result = await method(**params)
            else:
                # No params — call with no arguments
                result = await method()

            logger.info(
                "Executed action: %s.%s → %s",
                capability_name,
                action_name,
                "success" if result and "error" not in result else "error",
            )
            return result

        except TypeError as e:
            logger.error("Action parameter mismatch: %s — %s", action, e)
            return {"error": f"Invalid parameters for {action}: {e}"}
        except Exception as e:
            logger.error("Action execution failed: %s — %s", action, e)
            return {"error": f"Action failed: {e}"}

    async def store_memories(self, memory_entries: list):
        """Store new memory entries from the LLM response.

        Called immediately after every successful LLM call. Each entry in
        memory_store is passed to Memory.store().

        Entries that fail to store are logged but do not interrupt the flow.
        """
        for entry in memory_entries:
            if not isinstance(entry, dict):
                logger.warning("Skipping invalid memory entry: %s", entry)
                continue

            result = await self.memory.store(entry)
            if "error" in result:
                logger.warning(
                    "Failed to store memory entry: %s — %s",
                    entry.get("subject", "unknown"),
                    result["error"],
                )
            else:
                logger.info(
                    "Stored memory: [%s] %s",
                    entry.get("category", "unknown"),
                    entry.get("subject", "unknown"),
                )

    def _update_history(self, user_text: str, chitra_text: str):
        """Append the latest exchange to conversation history.

        Maintains a sliding window of the last N turns (from CHITRA_HISTORY_TURNS).
        Each turn is a pair of user + assistant messages.
        """
        self.conversation_history.append({"role": "user", "content": user_text})
        self.conversation_history.append({"role": "assistant", "content": chitra_text})

        # Trim to max_history_turns * 2 messages (each turn = 2 messages)
        max_messages = self.max_history_turns * 2
        if len(self.conversation_history) > max_messages:
            self.conversation_history = self.conversation_history[-max_messages:]

    async def _shutdown(self):
        """Clean shutdown — cancel background tasks, close connections."""
        logger.info("Shutting down Chitra...")

        # Cancel proactive loop
        if self._proactive_task and not self._proactive_task.done():
            self._proactive_task.cancel()
            try:
                await self._proactive_task
            except asyncio.CancelledError:
                pass

        # Close LLM client
        await self.llm.close()

        logger.info("Chitra shutdown complete")
