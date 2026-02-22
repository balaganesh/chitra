"""
Onboarding flow tests.

Tests:
- First run detection via marker file
- Onboarding step structure and completeness
- Input mode detection from natural language
- Empty answer detection
- Summary generation
- Memory seeding from onboarding answers
- Onboarding skipped on subsequent boots
"""

import os

import pytest

os.environ["CHITRA_DATA_DIR"] = "/tmp/chitra_test_onboarding"

from onboarding.flow import ONBOARDING_STEPS, OnboardingFlow
from orchestration.core import OrchestrationCore


@pytest.fixture
def fresh_data_dir(tmp_path):
    """Provide a fresh temporary data directory for each test."""
    data_dir = str(tmp_path / "chitra_data")
    os.makedirs(data_dir, exist_ok=True)
    os.environ["CHITRA_DATA_DIR"] = data_dir
    return data_dir


@pytest.fixture
def core(fresh_data_dir):
    """Create a fresh OrchestrationCore with isolated data."""
    return OrchestrationCore()


@pytest.fixture
def onboarding(core):
    """Create an OnboardingFlow instance."""
    return OnboardingFlow(core)


class TestOnboarding:
    """Tests for the first-run onboarding flow."""

    # ── First run detection ──────────────────────────────────

    @pytest.mark.asyncio
    async def test_should_run_first_boot(self, onboarding):
        """should_run returns True when no marker file exists."""
        assert await onboarding.should_run() is True

    @pytest.mark.asyncio
    async def test_should_run_after_complete(self, onboarding):
        """should_run returns False after onboarding marker is created."""
        onboarding._mark_complete()
        assert await onboarding.should_run() is False

    def test_mark_complete_creates_file(self, onboarding):
        """_mark_complete creates the .onboarding_complete marker file."""
        onboarding._mark_complete()
        assert os.path.exists(onboarding._onboarding_marker)

    def test_marker_path(self, onboarding, core):
        """Marker file is in the correct data directory."""
        expected = os.path.join(core.data_dir, ".onboarding_complete")
        assert onboarding._onboarding_marker == expected

    # ── Onboarding steps structure ───────────────────────────

    def test_step_count(self):
        """Onboarding has exactly 5 steps."""
        assert len(ONBOARDING_STEPS) == 5

    def test_all_topics_covered(self):
        """Onboarding covers name, input_mode, key_people, work_schedule, preferences."""
        subjects = [s["memory_subject"] for s in ONBOARDING_STEPS]
        assert "name" in subjects
        assert "input_mode" in subjects
        assert "key_people" in subjects
        assert "work_schedule" in subjects
        assert "initial_preferences" in subjects

    def test_each_step_has_required_fields(self):
        """Every step has prompt, memory_category, memory_subject, and format_content."""
        for i, step in enumerate(ONBOARDING_STEPS):
            assert "prompt" in step, f"Step {i} missing prompt"
            assert "memory_category" in step, f"Step {i} missing memory_category"
            assert "memory_subject" in step, f"Step {i} missing memory_subject"
            assert "format_content" in step, f"Step {i} missing format_content"
            assert callable(step["format_content"]), f"Step {i} format_content not callable"

    def test_valid_memory_categories(self):
        """All steps use valid memory categories."""
        valid = {"fact", "preference", "relationship", "observation"}
        for step in ONBOARDING_STEPS:
            assert step["memory_category"] in valid, (
                f"Invalid category: {step['memory_category']}"
            )

    # ── format_content lambdas ───────────────────────────────

    def test_format_name(self):
        """Name step formats content correctly."""
        step = ONBOARDING_STEPS[0]
        assert step["format_content"]("Bala") == "The user's name is Bala"

    def test_format_input_mode(self):
        """Input mode step formats content correctly."""
        step = ONBOARDING_STEPS[1]
        assert step["format_content"]("typing") == "Prefers typing input mode"

    def test_format_key_people(self):
        """Key people step passes through the answer directly."""
        step = ONBOARDING_STEPS[2]
        answer = "Amma is my mother, Ravi is my friend"
        assert step["format_content"](answer) == answer

    def test_format_work_schedule(self):
        """Work schedule step prefixes with 'Work schedule:'."""
        step = ONBOARDING_STEPS[3]
        assert step["format_content"]("9am to 6pm") == "Work schedule: 9am to 6pm"

    # ── Input mode detection ─────────────────────────────────

    @pytest.mark.asyncio
    async def test_process_input_mode_text(self, onboarding, core):
        """_process_input_mode detects text preference from natural language."""
        await onboarding._process_input_mode("I prefer typing")
        assert core.voice_io._input_mode == "text"

    @pytest.mark.asyncio
    async def test_process_input_mode_text_keyboard(self, onboarding, core):
        """_process_input_mode detects keyboard/text keywords."""
        await onboarding._process_input_mode("keyboard please")
        assert core.voice_io._input_mode == "text"

    @pytest.mark.asyncio
    async def test_process_input_mode_default(self, onboarding, core):
        """_process_input_mode defaults to text for ambiguous answers."""
        await onboarding._process_input_mode("whatever works")
        assert core.voice_io._input_mode == "text"

    # ── Empty answer detection ───────────────────────────────

    def test_is_empty_nothing(self, onboarding):
        """'nothing' is detected as empty."""
        assert onboarding._is_empty_answer("nothing") is True

    def test_is_empty_nothing_for_now(self, onboarding):
        """'Nothing for now' is detected as empty (case-insensitive)."""
        assert onboarding._is_empty_answer("Nothing for now") is True

    def test_is_empty_skip(self, onboarding):
        """'skip' is detected as empty."""
        assert onboarding._is_empty_answer("skip") is True

    def test_is_empty_no(self, onboarding):
        """'no' is detected as empty."""
        assert onboarding._is_empty_answer("no") is True

    def test_is_empty_nope(self, onboarding):
        """'nope' is detected as empty."""
        assert onboarding._is_empty_answer("nope") is True

    def test_is_not_empty_real_content(self, onboarding):
        """Real content is not detected as empty."""
        assert onboarding._is_empty_answer("I like coffee") is False

    def test_is_not_empty_yes(self, onboarding):
        """'yes' is not detected as empty."""
        assert onboarding._is_empty_answer("yes") is False

    # ── Summary generation ───────────────────────────────────

    def test_build_summary_with_memories(self, onboarding):
        """_build_summary generates summary with user name and memories."""
        memories = [
            {"category": "fact", "subject": "name", "content": "The user's name is Bala"},
            {"category": "preference", "subject": "input_mode", "content": "Prefers text"},
            {"category": "relationship", "subject": "key_people", "content": "Amma is mother"},
        ]
        summary = onboarding._build_summary("Bala", memories)
        assert "Bala" in summary
        assert "Prefers text" in summary
        assert "Amma" in summary

    def test_build_summary_skips_name(self, onboarding):
        """_build_summary does not repeat the name fact in the bullet list."""
        memories = [
            {"category": "fact", "subject": "name", "content": "The user's name is Bala"},
        ]
        summary = onboarding._build_summary("Bala", memories)
        # The name should be in the greeting but not as a bullet point
        assert "Bala" in summary
        assert "• The user's name is Bala" not in summary

    def test_build_summary_empty_memories(self, onboarding):
        """_build_summary handles empty memories gracefully."""
        summary = onboarding._build_summary(None, [])
        assert "all set" in summary.lower()

    def test_build_summary_no_name(self, onboarding):
        """_build_summary works when user name is None."""
        memories = [
            {"category": "preference", "subject": "coffee", "content": "Likes coffee"},
        ]
        summary = onboarding._build_summary(None, memories)
        assert "Likes coffee" in summary
