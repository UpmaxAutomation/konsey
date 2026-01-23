"""Tests for JSON-based storage module."""

import pytest
import json
import os
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path

from backend.storage import (
    ensure_data_dir,
    get_conversation_path,
    create_conversation,
    get_conversation,
    save_conversation,
    list_conversations,
    add_user_message,
    add_assistant_message,
    add_quick_message,
    update_conversation_title,
    delete_conversation,
    add_debate_message,
    get_conversation_context,
    # Folder functions
    get_folders_path,
    ensure_folders_file,
    list_folders,
    create_folder,
    delete_folder,
    move_conversation_to_folder,
    # Tag functions
    add_tag,
    remove_tag,
    update_tags,
    list_all_tags,
)


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary data directory for tests."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    with patch("backend.storage.DATA_DIR", str(data_dir)):
        yield data_dir


@pytest.fixture
def sample_conversation():
    """Create a sample conversation dict."""
    return {
        "id": "test-123",
        "created_at": "2024-01-15T10:00:00",
        "title": "Test Conversation",
        "messages": [],
        "folder_id": None,
        "tags": []
    }


# ============ PATH HELPER TESTS ============

class TestPathHelpers:
    """Tests for path helper functions."""

    def test_ensure_data_dir_creates_directory(self, temp_data_dir):
        """ensure_data_dir creates directory if it doesn't exist."""
        # Remove the dir to test creation
        os.rmdir(temp_data_dir)

        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            ensure_data_dir()

        assert temp_data_dir.exists()

    def test_get_conversation_path_format(self, temp_data_dir):
        """get_conversation_path returns correct path format."""
        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            path = get_conversation_path("conv-123")

        assert path == os.path.join(str(temp_data_dir), "conv-123.json")


# ============ CONVERSATION CRUD TESTS ============

class TestConversationCRUD:
    """Tests for conversation create/read/update/delete."""

    def test_create_conversation(self, temp_data_dir):
        """create_conversation creates a new conversation file."""
        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            conv = create_conversation("new-conv")

        assert conv["id"] == "new-conv"
        assert conv["title"] == "New Conversation"
        assert conv["messages"] == []
        assert conv["folder_id"] is None
        assert conv["tags"] == []
        assert "created_at" in conv

        # File should exist
        assert (temp_data_dir / "new-conv.json").exists()

    def test_get_conversation_exists(self, temp_data_dir, sample_conversation):
        """get_conversation returns existing conversation."""
        conv_path = temp_data_dir / "test-123.json"
        with open(conv_path, "w") as f:
            json.dump(sample_conversation, f)

        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            result = get_conversation("test-123")

        assert result["id"] == "test-123"
        assert result["title"] == "Test Conversation"

    def test_get_conversation_not_found(self, temp_data_dir):
        """get_conversation returns None for non-existent conversation."""
        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            result = get_conversation("non-existent")

        assert result is None

    def test_save_conversation(self, temp_data_dir, sample_conversation):
        """save_conversation persists conversation to file."""
        sample_conversation["title"] = "Updated Title"

        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            save_conversation(sample_conversation)

        conv_path = temp_data_dir / "test-123.json"
        with open(conv_path, "r") as f:
            saved = json.load(f)

        assert saved["title"] == "Updated Title"

    def test_delete_conversation_exists(self, temp_data_dir, sample_conversation):
        """delete_conversation removes existing conversation file."""
        conv_path = temp_data_dir / "test-123.json"
        with open(conv_path, "w") as f:
            json.dump(sample_conversation, f)

        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            result = delete_conversation("test-123")

        assert result is True
        assert not conv_path.exists()

    def test_delete_conversation_not_found(self, temp_data_dir):
        """delete_conversation returns False for non-existent conversation."""
        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            result = delete_conversation("non-existent")

        assert result is False

    def test_list_conversations(self, temp_data_dir):
        """list_conversations returns metadata for all conversations."""
        # Create multiple conversations
        for i in range(3):
            conv = {
                "id": f"conv-{i}",
                "created_at": f"2024-01-1{i}T10:00:00",
                "title": f"Conversation {i}",
                "messages": [{"role": "user", "content": "test"}] * i,
                "folder_id": None,
                "tags": [f"tag{i}"]
            }
            with open(temp_data_dir / f"conv-{i}.json", "w") as f:
                json.dump(conv, f)

        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            convs = list_conversations()

        assert len(convs) == 3
        # Should be sorted by created_at descending
        assert convs[0]["id"] == "conv-2"
        assert convs[0]["message_count"] == 2
        assert convs[0]["tags"] == ["tag2"]

    def test_list_conversations_excludes_folders_json(self, temp_data_dir):
        """list_conversations excludes folders.json from results."""
        # Create a conversation
        conv = {
            "id": "conv-1",
            "created_at": "2024-01-10T10:00:00",
            "title": "Conversation",
            "messages": [],
            "folder_id": None,
            "tags": []
        }
        with open(temp_data_dir / "conv-1.json", "w") as f:
            json.dump(conv, f)

        # Create folders.json
        with open(temp_data_dir / "folders.json", "w") as f:
            json.dump({"folders": []}, f)

        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            convs = list_conversations()

        assert len(convs) == 1
        assert convs[0]["id"] == "conv-1"


# ============ MESSAGE TESTS ============

class TestMessages:
    """Tests for message operations."""

    def test_add_user_message(self, temp_data_dir, sample_conversation):
        """add_user_message appends user message to conversation."""
        conv_path = temp_data_dir / "test-123.json"
        with open(conv_path, "w") as f:
            json.dump(sample_conversation, f)

        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            add_user_message("test-123", "Hello, world!")

        with open(conv_path, "r") as f:
            saved = json.load(f)

        assert len(saved["messages"]) == 1
        assert saved["messages"][0]["role"] == "user"
        assert saved["messages"][0]["content"] == "Hello, world!"

    def test_add_user_message_with_files(self, temp_data_dir, sample_conversation):
        """add_user_message includes attached files."""
        conv_path = temp_data_dir / "test-123.json"
        with open(conv_path, "w") as f:
            json.dump(sample_conversation, f)

        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            add_user_message("test-123", "Check this file", attached_files=["doc.pdf"])

        with open(conv_path, "r") as f:
            saved = json.load(f)

        assert saved["messages"][0]["attached_files"] == ["doc.pdf"]

    def test_add_user_message_not_found(self, temp_data_dir):
        """add_user_message raises ValueError for non-existent conversation."""
        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            with pytest.raises(ValueError, match="not found"):
                add_user_message("non-existent", "Hello")

    def test_add_assistant_message(self, temp_data_dir, sample_conversation):
        """add_assistant_message adds 3-stage council response."""
        conv_path = temp_data_dir / "test-123.json"
        with open(conv_path, "w") as f:
            json.dump(sample_conversation, f)

        stage1 = [{"model": "gpt-4", "response": "Answer 1"}]
        stage2 = [{"model": "gpt-4", "ranking": "1. Response A"}]
        stage3 = {"model": "gemini", "response": "Final answer"}

        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            add_assistant_message("test-123", stage1, stage2, stage3)

        with open(conv_path, "r") as f:
            saved = json.load(f)

        msg = saved["messages"][0]
        assert msg["role"] == "assistant"
        assert msg["type"] == "council"
        assert msg["stage1"] == stage1
        assert msg["stage2"] == stage2
        assert msg["stage3"] == stage3

    def test_add_quick_message(self, temp_data_dir, sample_conversation):
        """add_quick_message adds single-model response."""
        conv_path = temp_data_dir / "test-123.json"
        with open(conv_path, "w") as f:
            json.dump(sample_conversation, f)

        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            add_quick_message(
                "test-123",
                content="Quick response",
                model="gpt-4",
                thinking="Let me think...",
                usage={"input_tokens": 10, "output_tokens": 20}
            )

        with open(conv_path, "r") as f:
            saved = json.load(f)

        msg = saved["messages"][0]
        assert msg["role"] == "assistant"
        assert msg["type"] == "quick"
        assert msg["content"] == "Quick response"
        assert msg["model"] == "gpt-4"
        assert msg["thinking"] == "Let me think..."
        assert msg["usage"]["input_tokens"] == 10

    def test_add_debate_message(self, temp_data_dir, sample_conversation):
        """add_debate_message adds debate results."""
        conv_path = temp_data_dir / "test-123.json"
        with open(conv_path, "w") as f:
            json.dump(sample_conversation, f)

        debate_result = {
            "rounds": [{"round": 1, "responses": []}],
            "synthesis": "Final conclusion"
        }

        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            add_debate_message("test-123", debate_result)

        with open(conv_path, "r") as f:
            saved = json.load(f)

        msg = saved["messages"][0]
        assert msg["role"] == "assistant"
        assert msg["type"] == "debate"
        assert msg["debate"] == debate_result


# ============ TITLE UPDATE TESTS ============

class TestTitleUpdate:
    """Tests for conversation title updates."""

    def test_update_title(self, temp_data_dir, sample_conversation):
        """update_conversation_title changes the title."""
        conv_path = temp_data_dir / "test-123.json"
        with open(conv_path, "w") as f:
            json.dump(sample_conversation, f)

        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            update_conversation_title("test-123", "New Title")

        with open(conv_path, "r") as f:
            saved = json.load(f)

        assert saved["title"] == "New Title"

    def test_update_title_not_found(self, temp_data_dir):
        """update_conversation_title raises ValueError for non-existent conversation."""
        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            with pytest.raises(ValueError, match="not found"):
                update_conversation_title("non-existent", "Title")


# ============ CONTEXT EXTRACTION TESTS ============

class TestContextExtraction:
    """Tests for conversation context extraction."""

    def test_get_context_empty_conversation(self, temp_data_dir, sample_conversation):
        """get_conversation_context returns None for empty conversation."""
        conv_path = temp_data_dir / "test-123.json"
        with open(conv_path, "w") as f:
            json.dump(sample_conversation, f)

        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            context = get_conversation_context("test-123")

        assert context is None

    def test_get_context_with_exchanges(self, temp_data_dir, sample_conversation):
        """get_conversation_context extracts recent exchanges."""
        sample_conversation["messages"] = [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "stage3": {"response": "Python is a programming language."}},
            {"role": "user", "content": "What about Java?"},
            {"role": "assistant", "stage3": {"response": "Java is also a programming language."}},
        ]
        conv_path = temp_data_dir / "test-123.json"
        with open(conv_path, "w") as f:
            json.dump(sample_conversation, f)

        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            context = get_conversation_context("test-123", limit=2)

        assert "What is Python?" in context
        assert "What about Java?" in context
        assert "Python is a programming language" in context

    def test_get_context_respects_limit(self, temp_data_dir, sample_conversation):
        """get_conversation_context respects the limit parameter."""
        # Add 5 exchanges
        for i in range(5):
            sample_conversation["messages"].extend([
                {"role": "user", "content": f"Question {i}"},
                {"role": "assistant", "stage3": {"response": f"Answer {i}"}},
            ])

        conv_path = temp_data_dir / "test-123.json"
        with open(conv_path, "w") as f:
            json.dump(sample_conversation, f)

        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            context = get_conversation_context("test-123", limit=2)

        # Should only have the last 2 exchanges (3 and 4)
        assert "Question 3" in context
        assert "Question 4" in context
        assert "Question 0" not in context

    def test_get_context_not_found(self, temp_data_dir):
        """get_conversation_context returns None for non-existent conversation."""
        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            context = get_conversation_context("non-existent")

        assert context is None


# ============ FOLDER TESTS ============

class TestFolders:
    """Tests for folder management."""

    def test_ensure_folders_file_creates_defaults(self, temp_data_dir):
        """ensure_folders_file creates default folders."""
        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            ensure_folders_file()

        folders_path = temp_data_dir / "folders.json"
        assert folders_path.exists()

        with open(folders_path, "r") as f:
            data = json.load(f)

        assert len(data["folders"]) == 4  # clients, internal, archive, favorites
        folder_ids = [f["id"] for f in data["folders"]]
        assert "clients" in folder_ids
        assert "archive" in folder_ids

    def test_list_folders(self, temp_data_dir):
        """list_folders returns all folders."""
        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            ensure_folders_file()
            folders = list_folders()

        assert len(folders) == 4
        assert any(f["name"] == "Clients" for f in folders)

    def test_create_folder(self, temp_data_dir):
        """create_folder adds a new folder."""
        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            ensure_folders_file()
            new_folder = create_folder("My Project", color="#ff0000", icon="project")

        assert new_folder["name"] == "My Project"
        assert new_folder["color"] == "#ff0000"
        assert new_folder["icon"] == "project"
        assert new_folder["id"] == "my_project"

    def test_create_folder_unique_id(self, temp_data_dir):
        """create_folder generates unique ID if name exists."""
        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            ensure_folders_file()
            folder1 = create_folder("Test")
            folder2 = create_folder("Test")  # Same name

        assert folder1["id"] == "test"
        assert folder2["id"] == "test_1"

    def test_delete_folder(self, temp_data_dir):
        """delete_folder removes folder and updates conversations."""
        # Create a folder
        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            ensure_folders_file()
            create_folder("To Delete")

            # Create a conversation in that folder
            conv = {
                "id": "conv-1",
                "created_at": "2024-01-10T10:00:00",
                "title": "Test",
                "messages": [],
                "folder_id": "to_delete",
                "tags": []
            }
            with open(temp_data_dir / "conv-1.json", "w") as f:
                json.dump(conv, f)

            # Delete the folder
            result = delete_folder("to_delete")

        assert result is True

        # Conversation should have folder_id set to None
        with open(temp_data_dir / "conv-1.json", "r") as f:
            updated_conv = json.load(f)
        assert updated_conv["folder_id"] is None

    def test_delete_folder_not_found(self, temp_data_dir):
        """delete_folder returns False for non-existent folder."""
        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            ensure_folders_file()
            result = delete_folder("non-existent")

        assert result is False

    def test_move_conversation_to_folder(self, temp_data_dir, sample_conversation):
        """move_conversation_to_folder updates folder_id."""
        conv_path = temp_data_dir / "test-123.json"
        with open(conv_path, "w") as f:
            json.dump(sample_conversation, f)

        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            result = move_conversation_to_folder("test-123", "clients")

        assert result is True

        with open(conv_path, "r") as f:
            saved = json.load(f)
        assert saved["folder_id"] == "clients"

    def test_move_conversation_remove_from_folder(self, temp_data_dir, sample_conversation):
        """move_conversation_to_folder can remove from folder."""
        sample_conversation["folder_id"] = "clients"
        conv_path = temp_data_dir / "test-123.json"
        with open(conv_path, "w") as f:
            json.dump(sample_conversation, f)

        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            result = move_conversation_to_folder("test-123", None)

        assert result is True

        with open(conv_path, "r") as f:
            saved = json.load(f)
        assert saved["folder_id"] is None


# ============ TAG TESTS ============

class TestTags:
    """Tests for tag management."""

    def test_add_tag(self, temp_data_dir, sample_conversation):
        """add_tag appends tag to conversation."""
        conv_path = temp_data_dir / "test-123.json"
        with open(conv_path, "w") as f:
            json.dump(sample_conversation, f)

        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            result = add_tag("test-123", "important")

        assert result is True

        with open(conv_path, "r") as f:
            saved = json.load(f)
        assert "important" in saved["tags"]

    def test_add_tag_duplicate(self, temp_data_dir, sample_conversation):
        """add_tag doesn't add duplicate tags."""
        sample_conversation["tags"] = ["important"]
        conv_path = temp_data_dir / "test-123.json"
        with open(conv_path, "w") as f:
            json.dump(sample_conversation, f)

        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            add_tag("test-123", "important")

        with open(conv_path, "r") as f:
            saved = json.load(f)
        assert saved["tags"].count("important") == 1

    def test_remove_tag(self, temp_data_dir, sample_conversation):
        """remove_tag removes tag from conversation."""
        sample_conversation["tags"] = ["important", "urgent"]
        conv_path = temp_data_dir / "test-123.json"
        with open(conv_path, "w") as f:
            json.dump(sample_conversation, f)

        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            result = remove_tag("test-123", "important")

        assert result is True

        with open(conv_path, "r") as f:
            saved = json.load(f)
        assert "important" not in saved["tags"]
        assert "urgent" in saved["tags"]

    def test_update_tags(self, temp_data_dir, sample_conversation):
        """update_tags replaces all tags."""
        sample_conversation["tags"] = ["old1", "old2"]
        conv_path = temp_data_dir / "test-123.json"
        with open(conv_path, "w") as f:
            json.dump(sample_conversation, f)

        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            result = update_tags("test-123", ["new1", "new2", "new3"])

        assert result is True

        with open(conv_path, "r") as f:
            saved = json.load(f)
        assert saved["tags"] == ["new1", "new2", "new3"]

    def test_list_all_tags(self, temp_data_dir):
        """list_all_tags returns all unique tags across conversations."""
        # Create conversations with tags
        for i, tags in enumerate([["python", "ai"], ["javascript"], ["python", "web"]]):
            conv = {
                "id": f"conv-{i}",
                "created_at": "2024-01-10T10:00:00",
                "title": f"Conv {i}",
                "messages": [],
                "folder_id": None,
                "tags": tags
            }
            with open(temp_data_dir / f"conv-{i}.json", "w") as f:
                json.dump(conv, f)

        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            all_tags = list_all_tags()

        assert sorted(all_tags) == ["ai", "javascript", "python", "web"]

    def test_add_tag_not_found(self, temp_data_dir):
        """add_tag returns False for non-existent conversation."""
        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            result = add_tag("non-existent", "tag")

        assert result is False

    def test_remove_tag_not_found(self, temp_data_dir):
        """remove_tag returns False for non-existent conversation."""
        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            result = remove_tag("non-existent", "tag")

        assert result is False

    def test_update_tags_not_found(self, temp_data_dir):
        """update_tags returns False for non-existent conversation."""
        with patch("backend.storage.DATA_DIR", str(temp_data_dir)):
            result = update_tags("non-existent", ["tag"])

        assert result is False
