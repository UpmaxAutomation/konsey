"""Tests for External Integrations module."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestIntegrationType:
    """Tests for IntegrationType enum."""

    def test_type_values(self):
        from integrations import IntegrationType

        assert IntegrationType.GOOGLE_DRIVE.value == "google_drive"
        assert IntegrationType.SLACK.value == "slack"
        assert IntegrationType.GITHUB.value == "github"


class TestIntegrationStatus:
    """Tests for IntegrationStatus enum."""

    def test_status_values(self):
        from integrations import IntegrationStatus

        assert IntegrationStatus.CONNECTED.value == "connected"
        assert IntegrationStatus.DISCONNECTED.value == "disconnected"
        assert IntegrationStatus.ERROR.value == "error"


class TestIntegrationConfig:
    """Tests for IntegrationConfig dataclass."""

    def test_config_creation(self):
        from integrations import IntegrationConfig, IntegrationType, IntegrationStatus

        config = IntegrationConfig(type=IntegrationType.GITHUB)

        assert config.type == IntegrationType.GITHUB
        assert config.enabled is False
        assert config.status == IntegrationStatus.DISCONNECTED
        assert config.access_token is None

    def test_config_with_token(self):
        from integrations import IntegrationConfig, IntegrationType, IntegrationStatus

        config = IntegrationConfig(
            type=IntegrationType.SLACK,
            enabled=True,
            status=IntegrationStatus.CONNECTED,
            access_token="xoxb-test-token"
        )

        assert config.enabled is True
        assert config.access_token == "xoxb-test-token"


class TestSlackSendMessage:
    """Tests for slack_send_message function."""

    @pytest.mark.asyncio
    async def test_missing_token(self):
        from integrations import slack_send_message

        with patch.dict("os.environ", {"SLACK_BOT_TOKEN": ""}):
            import importlib
            import integrations
            importlib.reload(integrations)

            result = await integrations.slack_send_message("#general", "Hello")

            assert "error" in result
            assert "token" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_successful_message(self):
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "ok": True,
            "channel": "C123456",
            "ts": "1234567890.123456",
            "message": {"text": "Hello"}
        })

        with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}):
            with patch("aiohttp.ClientSession") as mock_session:
                mock_session.return_value.__aenter__ = AsyncMock(
                    return_value=MagicMock(
                        post=MagicMock(return_value=AsyncMock(
                            __aenter__=AsyncMock(return_value=mock_response),
                            __aexit__=AsyncMock()
                        ))
                    )
                )
                mock_session.return_value.__aexit__ = AsyncMock()

                import importlib
                import integrations
                importlib.reload(integrations)

                result = await integrations.slack_send_message("#general", "Hello")

                assert result["success"] is True
                assert result["channel"] == "C123456"


class TestSlackSendWebhook:
    """Tests for slack_send_webhook function."""

    @pytest.mark.asyncio
    async def test_missing_webhook(self):
        from integrations import slack_send_webhook

        with patch.dict("os.environ", {"SLACK_WEBHOOK_URL": ""}):
            import importlib
            import integrations
            importlib.reload(integrations)

            result = await integrations.slack_send_webhook("Test message")

            assert "error" in result
            assert "webhook" in result["error"].lower()


class TestSlackListChannels:
    """Tests for slack_list_channels function."""

    @pytest.mark.asyncio
    async def test_missing_token(self):
        from integrations import slack_list_channels

        with patch.dict("os.environ", {"SLACK_BOT_TOKEN": ""}):
            import importlib
            import integrations
            importlib.reload(integrations)

            result = await integrations.slack_list_channels()

            assert "error" in result

    @pytest.mark.asyncio
    async def test_successful_list(self):
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "ok": True,
            "channels": [
                {"id": "C1", "name": "general", "is_private": False, "num_members": 50},
                {"id": "C2", "name": "random", "is_private": False, "num_members": 30}
            ]
        })

        with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}):
            with patch("aiohttp.ClientSession") as mock_session:
                mock_session.return_value.__aenter__ = AsyncMock(
                    return_value=MagicMock(
                        get=MagicMock(return_value=AsyncMock(
                            __aenter__=AsyncMock(return_value=mock_response),
                            __aexit__=AsyncMock()
                        ))
                    )
                )
                mock_session.return_value.__aexit__ = AsyncMock()

                import importlib
                import integrations
                importlib.reload(integrations)

                result = await integrations.slack_list_channels()

                assert "channels" in result
                assert len(result["channels"]) == 2
                assert result["channels"][0]["name"] == "general"


class TestGitHubListRepos:
    """Tests for github_list_repos function."""

    @pytest.mark.asyncio
    async def test_missing_token(self):
        from integrations import github_list_repos

        with patch.dict("os.environ", {"GITHUB_TOKEN": ""}):
            import importlib
            import integrations
            importlib.reload(integrations)

            result = await integrations.github_list_repos()

            assert "error" in result
            assert "token" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_successful_list(self):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[
            {
                "id": 1,
                "name": "test-repo",
                "full_name": "user/test-repo",
                "description": "A test repo",
                "html_url": "https://github.com/user/test-repo",
                "language": "Python",
                "stargazers_count": 10,
                "forks_count": 5,
                "updated_at": "2024-01-01T00:00:00Z",
                "private": False
            }
        ])

        with patch.dict("os.environ", {"GITHUB_TOKEN": "ghp_test"}):
            with patch("aiohttp.ClientSession") as mock_session:
                mock_session.return_value.__aenter__ = AsyncMock(
                    return_value=MagicMock(
                        get=MagicMock(return_value=AsyncMock(
                            __aenter__=AsyncMock(return_value=mock_response),
                            __aexit__=AsyncMock()
                        ))
                    )
                )
                mock_session.return_value.__aexit__ = AsyncMock()

                import importlib
                import integrations
                importlib.reload(integrations)

                result = await integrations.github_list_repos()

                assert "repos" in result
                assert len(result["repos"]) == 1
                assert result["repos"][0]["name"] == "test-repo"


class TestGitHubGetFile:
    """Tests for github_get_file function."""

    @pytest.mark.asyncio
    async def test_missing_token(self):
        from integrations import github_get_file

        with patch.dict("os.environ", {"GITHUB_TOKEN": ""}):
            import importlib
            import integrations
            importlib.reload(integrations)

            result = await integrations.github_get_file("owner", "repo", "path.txt")

            assert "error" in result


class TestGitHubListIssues:
    """Tests for github_list_issues function."""

    @pytest.mark.asyncio
    async def test_missing_token(self):
        from integrations import github_list_issues

        with patch.dict("os.environ", {"GITHUB_TOKEN": ""}):
            import importlib
            import integrations
            importlib.reload(integrations)

            result = await integrations.github_list_issues("owner", "repo")

            assert "error" in result

    @pytest.mark.asyncio
    async def test_successful_list(self):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[
            {
                "number": 1,
                "title": "Bug fix",
                "state": "open",
                "html_url": "https://github.com/owner/repo/issues/1",
                "user": {"login": "user1"},
                "labels": [{"name": "bug"}],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z"
            }
        ])

        with patch.dict("os.environ", {"GITHUB_TOKEN": "ghp_test"}):
            with patch("aiohttp.ClientSession") as mock_session:
                mock_session.return_value.__aenter__ = AsyncMock(
                    return_value=MagicMock(
                        get=MagicMock(return_value=AsyncMock(
                            __aenter__=AsyncMock(return_value=mock_response),
                            __aexit__=AsyncMock()
                        ))
                    )
                )
                mock_session.return_value.__aexit__ = AsyncMock()

                import importlib
                import integrations
                importlib.reload(integrations)

                result = await integrations.github_list_issues("owner", "repo")

                assert "issues" in result
                assert len(result["issues"]) == 1
                assert result["issues"][0]["title"] == "Bug fix"


class TestGitHubCreateIssue:
    """Tests for github_create_issue function."""

    @pytest.mark.asyncio
    async def test_missing_token(self):
        from integrations import github_create_issue

        with patch.dict("os.environ", {"GITHUB_TOKEN": ""}):
            import importlib
            import integrations
            importlib.reload(integrations)

            result = await integrations.github_create_issue(
                "owner", "repo", "Title", "Body"
            )

            assert "error" in result


class TestGitHubListPRs:
    """Tests for github_list_prs function."""

    @pytest.mark.asyncio
    async def test_missing_token(self):
        from integrations import github_list_prs

        with patch.dict("os.environ", {"GITHUB_TOKEN": ""}):
            import importlib
            import integrations
            importlib.reload(integrations)

            result = await integrations.github_list_prs("owner", "repo")

            assert "error" in result

    @pytest.mark.asyncio
    async def test_successful_list(self):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[
            {
                "number": 5,
                "title": "Feature PR",
                "state": "open",
                "html_url": "https://github.com/owner/repo/pull/5",
                "user": {"login": "user2"},
                "head": {"ref": "feature-branch"},
                "base": {"ref": "main"},
                "created_at": "2024-01-05T00:00:00Z",
                "updated_at": "2024-01-06T00:00:00Z",
                "mergeable": True,
                "draft": False
            }
        ])

        with patch.dict("os.environ", {"GITHUB_TOKEN": "ghp_test"}):
            with patch("aiohttp.ClientSession") as mock_session:
                mock_session.return_value.__aenter__ = AsyncMock(
                    return_value=MagicMock(
                        get=MagicMock(return_value=AsyncMock(
                            __aenter__=AsyncMock(return_value=mock_response),
                            __aexit__=AsyncMock()
                        ))
                    )
                )
                mock_session.return_value.__aexit__ = AsyncMock()

                import importlib
                import integrations
                importlib.reload(integrations)

                result = await integrations.github_list_prs("owner", "repo")

                assert "pull_requests" in result
                assert len(result["pull_requests"]) == 1
                assert result["pull_requests"][0]["title"] == "Feature PR"


class TestGDriveListFiles:
    """Tests for gdrive_list_files function."""

    @pytest.mark.asyncio
    async def test_successful_list(self):
        from integrations import gdrive_list_files

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "files": [
                {"id": "file1", "name": "Document.docx", "mimeType": "application/vnd.google-apps.document"}
            ],
            "nextPageToken": None
        })

        with patch("aiohttp.ClientSession") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(
                    get=MagicMock(return_value=AsyncMock(
                        __aenter__=AsyncMock(return_value=mock_response),
                        __aexit__=AsyncMock()
                    ))
                )
            )
            mock_session.return_value.__aexit__ = AsyncMock()

            result = await gdrive_list_files("access_token_here")

            assert "files" in result
            assert len(result["files"]) == 1


class TestGetIntegrationStatus:
    """Tests for get_integration_status function."""

    def test_status_structure(self):
        from integrations import get_integration_status

        status = get_integration_status()

        assert "google_drive" in status
        assert "slack" in status
        assert "github" in status

        assert "available" in status["google_drive"]
        assert "features" in status["google_drive"]

    def test_slack_features(self):
        from integrations import get_integration_status

        status = get_integration_status()

        assert "Channel notifications" in status["slack"]["features"]
        assert "Webhooks" in status["slack"]["features"]

    def test_github_features(self):
        from integrations import get_integration_status

        status = get_integration_status()

        assert "Repository access" in status["github"]["features"]
        assert "Issues" in status["github"]["features"]
        assert "Pull requests" in status["github"]["features"]


class TestIntegrationConfigManagement:
    """Tests for integration config management functions."""

    def test_get_integration_config(self):
        from integrations import get_integration_config, set_integration_config, _integrations

        _integrations.clear()

        # Should return None for non-existent
        result = get_integration_config("github")
        assert result is None

    def test_set_integration_config(self):
        from integrations import set_integration_config, _integrations, IntegrationStatus

        _integrations.clear()

        config = set_integration_config(
            "github",
            enabled=True,
            access_token="ghp_test"
        )

        assert config.enabled is True
        assert config.access_token == "ghp_test"
        assert config.status == IntegrationStatus.CONNECTED
        assert "github" in _integrations
