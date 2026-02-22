"""
Memory-specific tests.

Tests:
- Memory storage and retrieval
- Context block assembly and formatting
- Context window management rules (from MEMORY_DESIGN.md)
- Memory search
- Memory update and deactivation
- Confidence and source validation
- Error handling
"""

import os

import pytest

os.environ["CHITRA_DATA_DIR"] = "/tmp/chitra_test_memory"

from capabilities.memory import Memory


@pytest.fixture
def memory(tmp_path):
    """Create a fresh Memory instance with isolated database."""
    db_path = str(tmp_path / "memory.db")
    return Memory(db_path)


@pytest.fixture
def sample_entries():
    """Standard set of memory entries for context tests."""
    return [
        {"category": "fact", "subject": "name", "content": "The user's name is Bala", "confidence": 1.0, "source": "stated"},
        {"category": "preference", "subject": "meetings", "content": "Prefers no meetings before 9am", "confidence": 1.0, "source": "stated"},
        {"category": "relationship", "subject": "mother", "content": "Mother prefers calls after 7pm", "confidence": 1.0, "source": "stated"},
        {"category": "observation", "subject": "routine", "content": "Usually starts the day around 9am", "confidence": 0.7, "source": "inferred"},
    ]


class TestMemoryStorage:
    """Tests for memory store and retrieval."""

    # ── Happy path ────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_store_fact(self, memory):
        """Storing a fact returns the entry with generated ID and timestamps."""
        result = await memory.store({
            "category": "fact",
            "subject": "job",
            "content": "Works at Flipkart",
        })
        assert "id" in result
        assert result["category"] == "fact"
        assert result["subject"] == "job"
        assert result["content"] == "Works at Flipkart"
        assert result["confidence"] == 1.0
        assert result["source"] == "stated"
        assert result["active"] is True
        assert result["created_at"] is not None
        assert result["last_referenced"] is not None

    @pytest.mark.asyncio
    async def test_store_preference(self, memory):
        """Storing a preference succeeds."""
        result = await memory.store({
            "category": "preference",
            "subject": "coffee",
            "content": "Likes strong filter coffee",
        })
        assert result["category"] == "preference"
        assert result["content"] == "Likes strong filter coffee"

    @pytest.mark.asyncio
    async def test_store_observation(self, memory):
        """Storing an observation with inferred source and custom confidence."""
        result = await memory.store({
            "category": "observation",
            "subject": "routine",
            "content": "Usually checks tasks at 9am",
            "confidence": 0.6,
            "source": "inferred",
        })
        assert result["confidence"] == 0.6
        assert result["source"] == "inferred"

    @pytest.mark.asyncio
    async def test_store_relationship(self, memory):
        """Storing a relationship with contact_id."""
        result = await memory.store({
            "category": "relationship",
            "subject": "mother",
            "content": "Mother prefers calls after 7pm",
            "contact_id": "contact-123",
        })
        assert result["contact_id"] == "contact-123"

    @pytest.mark.asyncio
    async def test_store_defaults(self, memory):
        """Default confidence is 1.0, source is 'stated', contact_id is None."""
        result = await memory.store({
            "category": "fact",
            "subject": "city",
            "content": "Lives in Bengaluru",
        })
        assert result["confidence"] == 1.0
        assert result["source"] == "stated"
        assert result["contact_id"] is None

    @pytest.mark.asyncio
    async def test_store_unique_ids(self, memory):
        """Each stored entry gets a unique ID."""
        r1 = await memory.store({"category": "fact", "subject": "a", "content": "A"})
        r2 = await memory.store({"category": "fact", "subject": "b", "content": "B"})
        assert r1["id"] != r2["id"]

    # ── Validation errors ─────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_store_missing_category(self, memory):
        """Missing category returns error."""
        result = await memory.store({"subject": "x", "content": "y"})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_store_missing_subject(self, memory):
        """Missing subject returns error."""
        result = await memory.store({"category": "fact", "content": "y"})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_store_missing_content(self, memory):
        """Missing content returns error."""
        result = await memory.store({"category": "fact", "subject": "x"})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_store_invalid_category(self, memory):
        """Invalid category returns error."""
        result = await memory.store({
            "category": "invalid",
            "subject": "x",
            "content": "y",
        })
        assert "error" in result
        assert "Invalid category" in result["error"]

    @pytest.mark.asyncio
    async def test_store_invalid_source(self, memory):
        """Invalid source returns error."""
        result = await memory.store({
            "category": "fact",
            "subject": "x",
            "content": "y",
            "source": "guessed",
        })
        assert "error" in result
        assert "Invalid source" in result["error"]

    # ── Search ────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_search_by_subject(self, memory):
        """Search finds entries matching subject."""
        await memory.store({"category": "fact", "subject": "job", "content": "Works at Flipkart"})
        await memory.store({"category": "fact", "subject": "city", "content": "Lives in Bengaluru"})
        results = await memory.search("job")
        assert len(results) == 1
        assert results[0]["subject"] == "job"

    @pytest.mark.asyncio
    async def test_search_by_content(self, memory):
        """Search finds entries matching content."""
        await memory.store({"category": "fact", "subject": "work", "content": "Works at Flipkart in Bengaluru"})
        results = await memory.search("Flipkart")
        assert len(results) == 1
        assert "Flipkart" in results[0]["content"]

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, memory):
        """Search is case-insensitive via LIKE."""
        await memory.store({"category": "fact", "subject": "work", "content": "Works at FLIPKART"})
        results = await memory.search("flipkart")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_no_results(self, memory):
        """Search returns empty list when no match."""
        await memory.store({"category": "fact", "subject": "job", "content": "Works at Flipkart"})
        results = await memory.search("Amazon")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_excludes_inactive(self, memory):
        """Search does not return deactivated entries."""
        result = await memory.store({"category": "fact", "subject": "old", "content": "Old info"})
        await memory.deactivate(result["id"])
        results = await memory.search("old")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_ordered_by_confidence(self, memory):
        """Search results are ordered by confidence DESC."""
        await memory.store({"category": "observation", "subject": "a", "content": "Pattern A", "confidence": 0.5, "source": "inferred"})
        await memory.store({"category": "fact", "subject": "a", "content": "Fact A", "confidence": 1.0})
        results = await memory.search("A")
        assert len(results) == 2
        assert results[0]["confidence"] >= results[1]["confidence"]

    # ── Update ────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_update_content(self, memory):
        """Update changes the content of an existing entry."""
        original = await memory.store({"category": "preference", "subject": "meetings", "content": "No meetings before 9am"})
        updated = await memory.update(original["id"], "OK with 8am meetings now")
        assert updated["content"] == "OK with 8am meetings now"
        assert updated["id"] == original["id"]

    @pytest.mark.asyncio
    async def test_update_refreshes_last_referenced(self, memory):
        """Update refreshes last_referenced timestamp."""
        original = await memory.store({"category": "fact", "subject": "test", "content": "Original"})
        updated = await memory.update(original["id"], "Updated")
        assert updated["last_referenced"] >= original["last_referenced"]

    @pytest.mark.asyncio
    async def test_update_not_found(self, memory):
        """Update returns error for nonexistent ID."""
        result = await memory.update("nonexistent-id", "New content")
        assert "error" in result

    # ── Deactivate ────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_deactivate(self, memory):
        """Deactivate soft-deletes an entry."""
        stored = await memory.store({"category": "fact", "subject": "temp", "content": "Temporary info"})
        result = await memory.deactivate(stored["id"])
        assert result["status"] == "deactivated"

    @pytest.mark.asyncio
    async def test_deactivate_excludes_from_context(self, memory):
        """Deactivated entries are not included in context block."""
        stored = await memory.store({"category": "preference", "subject": "gone", "content": "Should disappear"})
        await memory.deactivate(stored["id"])
        ctx = await memory.get_context()
        assert "Should disappear" not in ctx["context_block"]

    @pytest.mark.asyncio
    async def test_deactivate_not_found(self, memory):
        """Deactivate returns error for nonexistent ID."""
        result = await memory.deactivate("nonexistent-id")
        assert "error" in result


class TestMemoryContext:
    """Tests for context block assembly and injection."""

    # ── Context block formatting ──────────────────────────────────

    @pytest.mark.asyncio
    async def test_empty_context(self, memory):
        """Empty memory returns empty context block."""
        ctx = await memory.get_context()
        assert ctx["context_block"] == ""

    @pytest.mark.asyncio
    async def test_context_includes_preferences(self, memory):
        """Context block includes all preferences."""
        await memory.store({"category": "preference", "subject": "coffee", "content": "Likes filter coffee"})
        ctx = await memory.get_context()
        assert "Likes filter coffee" in ctx["context_block"]

    @pytest.mark.asyncio
    async def test_context_includes_high_confidence_facts(self, memory):
        """Context block includes facts with confidence >= 0.8."""
        await memory.store({"category": "fact", "subject": "job", "content": "Works at Flipkart", "confidence": 1.0})
        await memory.store({"category": "fact", "subject": "guess", "content": "Maybe likes cricket", "confidence": 0.5, "source": "inferred"})
        ctx = await memory.get_context()
        assert "Works at Flipkart" in ctx["context_block"]
        assert "Maybe likes cricket" not in ctx["context_block"]

    @pytest.mark.asyncio
    async def test_context_includes_recent_relationships(self, memory):
        """Context block includes relationships referenced within 30 days."""
        result = await memory.store({"category": "relationship", "subject": "mother", "content": "Mother prefers evening calls"})
        # Freshly stored — last_referenced is now, well within 30 days
        ctx = await memory.get_context()
        assert "Mother prefers evening calls" in ctx["context_block"]

    @pytest.mark.asyncio
    async def test_context_includes_observations(self, memory):
        """Context block includes observations with confidence >= 0.5."""
        await memory.store({"category": "observation", "subject": "routine", "content": "Usually starts work at 9am", "confidence": 0.7, "source": "inferred"})
        ctx = await memory.get_context()
        assert "Usually starts work at 9am" in ctx["context_block"]

    @pytest.mark.asyncio
    async def test_context_excludes_low_confidence_facts(self, memory):
        """Context block excludes facts with confidence < 0.8."""
        await memory.store({"category": "fact", "subject": "maybe", "content": "Possibly works remotely", "confidence": 0.6, "source": "inferred"})
        ctx = await memory.get_context()
        assert "Possibly works remotely" not in ctx["context_block"]

    @pytest.mark.asyncio
    async def test_context_excludes_inactive(self, memory):
        """Context block excludes deactivated entries."""
        result = await memory.store({"category": "preference", "subject": "old", "content": "Old preference"})
        await memory.deactivate(result["id"])
        ctx = await memory.get_context()
        assert "Old preference" not in ctx["context_block"]

    # ── Context block structure ───────────────────────────────────

    @pytest.mark.asyncio
    async def test_context_has_about_section(self, memory):
        """Context block has 'About the user:' section for facts and preferences."""
        await memory.store({"category": "fact", "subject": "name", "content": "User is Bala", "confidence": 1.0})
        ctx = await memory.get_context()
        assert "About the user:" in ctx["context_block"]

    @pytest.mark.asyncio
    async def test_context_has_people_section(self, memory):
        """Context block has 'People:' section for relationships."""
        await memory.store({"category": "relationship", "subject": "friend", "content": "Ravi is a close friend"})
        ctx = await memory.get_context()
        assert "People:" in ctx["context_block"]

    @pytest.mark.asyncio
    async def test_context_has_patterns_section(self, memory):
        """Context block has 'Current patterns:' section for observations."""
        await memory.store({"category": "observation", "subject": "habit", "content": "Checks tasks every morning", "confidence": 0.7, "source": "inferred"})
        ctx = await memory.get_context()
        assert "Current patterns:" in ctx["context_block"]

    @pytest.mark.asyncio
    async def test_context_multiple_sections(self, memory, sample_entries):
        """Context block contains all three sections when all categories present."""
        for entry in sample_entries:
            await memory.store(entry)
        ctx = await memory.get_context()
        block = ctx["context_block"]
        assert "About the user:" in block
        assert "People:" in block
        assert "Current patterns:" in block

    # ── last_referenced tracking ──────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_context_updates_last_referenced_for_included(self, memory):
        """get_context updates last_referenced only for included entries."""
        import sqlite3

        stored = await memory.store({"category": "preference", "subject": "test", "content": "Test preference"})
        original_ref = stored["last_referenced"]

        # Call get_context — should update last_referenced
        await memory.get_context()

        conn = sqlite3.connect(memory.db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT last_referenced FROM memories WHERE id = ?", (stored["id"],)).fetchone()
        conn.close()

        assert row["last_referenced"] >= original_ref

    @pytest.mark.asyncio
    async def test_get_context_does_not_update_excluded(self, memory):
        """get_context does not update last_referenced for excluded entries."""
        import sqlite3

        # Store a low-confidence fact that should be excluded (< 0.8)
        stored = await memory.store({
            "category": "fact",
            "subject": "guess",
            "content": "Maybe something",
            "confidence": 0.5,
            "source": "inferred",
        })
        original_ref = stored["last_referenced"]

        await memory.get_context()

        conn = sqlite3.connect(memory.db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT last_referenced FROM memories WHERE id = ?", (stored["id"],)).fetchone()
        conn.close()

        # Should not have been updated since it was excluded
        assert row["last_referenced"] == original_ref

    # ── Context window rules: relationship aging ──────────────────

    @pytest.mark.asyncio
    async def test_old_relationship_excluded(self, memory):
        """Relationships not referenced within 30 days are excluded."""
        import sqlite3

        stored = await memory.store({"category": "relationship", "subject": "old_friend", "content": "Old friend from school"})

        # Manually set last_referenced to 31 days ago
        from datetime import datetime, timedelta
        old_date = (datetime.now() - timedelta(days=31)).isoformat()
        conn = sqlite3.connect(memory.db_path)
        conn.execute("UPDATE memories SET last_referenced = ? WHERE id = ?", (old_date, stored["id"]))
        conn.commit()
        conn.close()

        ctx = await memory.get_context()
        assert "Old friend from school" not in ctx["context_block"]

    @pytest.mark.asyncio
    async def test_recent_relationship_included(self, memory):
        """Relationships referenced within 30 days are included."""
        import sqlite3

        stored = await memory.store({"category": "relationship", "subject": "recent_friend", "content": "Recent friend Ravi"})

        # Set last_referenced to 15 days ago — still within 30-day window
        from datetime import datetime, timedelta
        recent_date = (datetime.now() - timedelta(days=15)).isoformat()
        conn = sqlite3.connect(memory.db_path)
        conn.execute("UPDATE memories SET last_referenced = ? WHERE id = ?", (recent_date, stored["id"]))
        conn.commit()
        conn.close()

        ctx = await memory.get_context()
        assert "Recent friend Ravi" in ctx["context_block"]
