"""Tests for database CRUD operations."""

import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from backend.database.models import User, UserSettings, UserAPIKey, Conversation, Message


class TestUsersCRUD:
    """Tests for user CRUD operations."""

    @pytest.fixture
    def mock_db(self):
        """Mock async database session."""
        db = AsyncMock()
        return db

    @pytest.fixture
    def sample_user(self):
        """Sample user object."""
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            password_hash="hashed_password",
            name="Test User",
            is_active=True,
            is_verified=False,
            is_admin=False,
        )
        return user

    @pytest.mark.asyncio
    async def test_create_user(self, mock_db, sample_user):
        """Test creating a new user."""
        from backend.database.crud import users

        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        with patch.object(users, "hash_password", return_value="hashed"):
            result = await users.create(
                mock_db,
                email="new@example.com",
                password="securepassword"
            )

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        assert result.email == "new@example.com"

    @pytest.mark.asyncio
    async def test_get_by_email(self, mock_db, sample_user):
        """Test getting user by email."""
        from backend.database.crud import users

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await users.get_by_email(mock_db, "test@example.com")

        assert result == sample_user
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, mock_db):
        """Test getting non-existent user by email."""
        from backend.database.crud import users

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await users.get_by_email(mock_db, "nonexistent@example.com")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id(self, mock_db, sample_user):
        """Test getting user by ID."""
        from backend.database.crud import users

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await users.get_by_id(mock_db, sample_user.id)

        assert result == sample_user


class TestSettingsCRUD:
    """Tests for user settings CRUD operations."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        return db

    @pytest.fixture
    def sample_settings(self):
        return UserSettings(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            council_models=["openai/gpt-4o", "anthropic/claude-sonnet-4"],
            chairman_model="google/gemini-2.5-flash",
        )

    @pytest.mark.asyncio
    async def test_get_by_user_id(self, mock_db, sample_settings):
        """Test getting settings by user ID."""
        from backend.database.crud import settings

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_settings
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await settings.get_by_user_id(mock_db, sample_settings.user_id)

        assert result == sample_settings

    @pytest.mark.asyncio
    async def test_create_default_settings(self, mock_db):
        """Test creating default settings for a user."""
        from backend.database.crud import settings

        user_id = uuid.uuid4()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        result = await settings.create(mock_db, user_id)

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        assert result.user_id == user_id
        assert len(result.council_models) > 0  # Default models set

    @pytest.mark.asyncio
    async def test_update_council_config(self, mock_db, sample_settings):
        """Test updating council configuration."""
        from backend.database.crud import settings

        mock_db.execute = AsyncMock()

        # Mock get_by_user_id for the return value
        with patch.object(settings, "get_by_user_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = sample_settings

            result = await settings.set_council_config(
                mock_db,
                sample_settings.user_id,
                council_models=["model-1", "model-2"],
                chairman_model="model-chair"
            )

        mock_db.execute.assert_called()


class TestAPIKeysCRUD:
    """Tests for API key CRUD operations."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_get_user_key(self, mock_db):
        """Test getting user's API key for a provider."""
        from backend.database.crud import api_keys

        user_id = uuid.uuid4()
        mock_key = UserAPIKey(
            id=uuid.uuid4(),
            user_id=user_id,
            provider="openai",
            encrypted_key="encrypted_value",
            is_active=True,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_key
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch.object(api_keys, "decrypt_key", return_value="sk-real-key"):
            result = await api_keys.get_user_key(mock_db, user_id, "openai")

        assert result == "sk-real-key"

    @pytest.mark.asyncio
    async def test_get_user_key_not_found(self, mock_db):
        """Test getting non-existent API key."""
        from backend.database.crud import api_keys

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await api_keys.get_user_key(mock_db, uuid.uuid4(), "nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_system_key(self, mock_db):
        """Test getting system-level API key."""
        from backend.database.crud import api_keys

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(value="encrypted_system_key")
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch.object(api_keys, "decrypt_key", return_value="system-key-value"):
            result = await api_keys.get_system_key(mock_db, "openrouter")

        assert result == "system-key-value"

    @pytest.mark.asyncio
    async def test_resolve_api_key_user_first(self, mock_db):
        """Test that user key takes precedence over system key."""
        from backend.database.crud import api_keys

        user_id = uuid.uuid4()

        # Mock user key exists
        with patch.object(api_keys, "get_user_key", new_callable=AsyncMock) as mock_user, \
             patch.object(api_keys, "get_system_key", new_callable=AsyncMock) as mock_system:

            mock_user.return_value = "user-key"
            mock_system.return_value = "system-key"

            result = await api_keys.resolve_api_key(mock_db, user_id, "openai")

        assert result == "user-key"
        mock_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_resolve_api_key_fallback_to_system(self, mock_db):
        """Test fallback to system key when user key not found."""
        from backend.database.crud import api_keys

        user_id = uuid.uuid4()

        with patch.object(api_keys, "get_user_key", new_callable=AsyncMock) as mock_user, \
             patch.object(api_keys, "get_system_key", new_callable=AsyncMock) as mock_system:

            mock_user.return_value = None
            mock_system.return_value = "system-key"

            result = await api_keys.resolve_api_key(
                mock_db, user_id, "openai", allow_system_fallback=True
            )

        assert result == "system-key"


class TestConversationsCRUD:
    """Tests for conversation CRUD operations."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def sample_conversation(self):
        return Conversation(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            title="Test Conversation",
            created_at=datetime.utcnow(),
        )

    @pytest.mark.asyncio
    async def test_create_conversation(self, mock_db):
        """Test creating a new conversation."""
        from backend.database.crud import conversations

        user_id = uuid.uuid4()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        result = await conversations.create(mock_db, user_id, title="New Chat")

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        assert result.user_id == user_id
        assert result.title == "New Chat"

    @pytest.mark.asyncio
    async def test_get_conversation_by_id(self, mock_db, sample_conversation):
        """Test getting conversation by ID."""
        from backend.database.crud import conversations

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_conversation
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await conversations.get_by_id(mock_db, sample_conversation.id)

        assert result == sample_conversation

    @pytest.mark.asyncio
    async def test_list_user_conversations(self, mock_db, sample_conversation):
        """Test listing user's conversations."""
        from backend.database.crud import conversations

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_conversation]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await conversations.list_by_user(mock_db, sample_conversation.user_id)

        assert len(result) == 1
        assert result[0] == sample_conversation

    @pytest.mark.asyncio
    async def test_update_title(self, mock_db, sample_conversation):
        """Test updating conversation title."""
        from backend.database.crud import conversations

        mock_db.execute = AsyncMock()

        with patch.object(conversations, "get_by_id", new_callable=AsyncMock) as mock_get:
            sample_conversation.title = "Updated Title"
            mock_get.return_value = sample_conversation

            result = await conversations.update_title(
                mock_db, sample_conversation.id, "Updated Title"
            )

        assert result.title == "Updated Title"

    @pytest.mark.asyncio
    async def test_delete_conversation(self, mock_db, sample_conversation):
        """Test deleting a conversation."""
        from backend.database.crud import conversations

        mock_db.execute = AsyncMock()

        result = await conversations.delete(mock_db, sample_conversation.id)

        mock_db.execute.assert_called_once()


class TestUsageCRUD:
    """Tests for usage tracking CRUD operations."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_record_usage(self, mock_db):
        """Test recording API usage."""
        from backend.database.crud import usage

        user_id = uuid.uuid4()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        result = await usage.record_usage(
            mock_db,
            user_id,
            model="openai/gpt-4o",
            input_tokens=100,
            output_tokens=50,
            cost=0.005
        )

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        assert result.user_id == user_id
        assert result.model == "openai/gpt-4o"
        assert result.input_tokens == 100

    @pytest.mark.asyncio
    async def test_get_session_usage(self, mock_db):
        """Test getting aggregated session usage."""
        from backend.database.crud import usage

        user_id = uuid.uuid4()

        # Mock aggregation result
        mock_row = MagicMock()
        mock_row.total_input = 1000
        mock_row.total_output = 500
        mock_row.total_cost = 0.05
        mock_row.request_count = 10

        mock_result = MagicMock()
        mock_result.one.return_value = mock_row
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await usage.get_session_usage(mock_db, user_id)

        assert result["total_input_tokens"] == 1000
        assert result["total_output_tokens"] == 500
        assert result["total_cost"] == 0.05
        assert result["request_count"] == 10


class TestMemoryCRUD:
    """Tests for user memory CRUD operations."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_add_fact(self, mock_db):
        """Test adding a fact to user memory."""
        from backend.database.crud import memory

        user_id = uuid.uuid4()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.execute = AsyncMock()  # For pruning

        with patch.object(memory, "_prune_memories", new_callable=AsyncMock):
            result = await memory.add_fact(
                mock_db,
                user_id,
                "Python is a programming language",
                category="technical"
            )

        mock_db.add.assert_called_once()
        assert result.user_id == user_id
        assert result.memory_type == "fact"

    @pytest.mark.asyncio
    async def test_add_decision(self, mock_db):
        """Test adding a decision to user memory."""
        from backend.database.crud import memory

        user_id = uuid.uuid4()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        with patch.object(memory, "_prune_memories", new_callable=AsyncMock):
            result = await memory.add_decision(
                mock_db,
                user_id,
                question="Should we use React?",
                decision="Yes, for component reusability",
                reasoning="Better ecosystem"
            )

        assert result.memory_type == "decision"

    @pytest.mark.asyncio
    async def test_get_memory_context(self, mock_db):
        """Test getting formatted memory context."""
        from backend.database.crud import memory

        user_id = uuid.uuid4()

        # Mock empty results
        with patch.object(memory, "get_facts", new_callable=AsyncMock) as mock_facts, \
             patch.object(memory, "get_decisions", new_callable=AsyncMock) as mock_decisions, \
             patch.object(memory, "get_preferences", new_callable=AsyncMock) as mock_prefs:

            mock_facts.return_value = [
                {"content": "Python fact", "category": "technical", "timestamp": "2024-01-01"}
            ]
            mock_decisions.return_value = []
            mock_prefs.return_value = {}

            result = await memory.get_memory_context(mock_db, user_id)

        assert "Python fact" in result
        assert "**Remembered Facts:**" in result
