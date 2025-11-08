from unittest.mock import Mock

import pytest
from selenium.common.exceptions import WebDriverException
import src.driver as driver_module
from src.driver import get_fresh_driver, is_session_alive
# =================================


def test_get_fresh_driver_closes_existing_and_builds_new(monkeypatch):
    captured = {}
    built_driver = object()

    def fake_build_driver(account_name=None, profile_base_dir=None, headless=True):
        captured["account_name"] = account_name
        captured["profile_base_dir"] = profile_base_dir
        captured["headless"] = headless
        return built_driver

    monkeypatch.setattr(driver_module, "build_driver", fake_build_driver)

    existing = Mock()
    result = get_fresh_driver(
        existing=existing,
        profile_base_dir="/tmp/profiles",
        account_name="test-account",
        headless=False,
    )

    existing.quit.assert_called_once_with()
    assert result is built_driver
    assert captured == {
        "account_name": "test-account",
        "profile_base_dir": "/tmp/profiles",
        "headless": False,
    }


def test_get_fresh_driver_without_existing(monkeypatch):
    def fake_build_driver(account_name=None, profile_base_dir=None, headless=True):
        assert account_name is None
        assert profile_base_dir is None
        assert headless is True
        return "fresh"

    monkeypatch.setattr(driver_module, "build_driver", fake_build_driver)
    assert get_fresh_driver(existing=None) == "fresh"


def test_is_session_alive_true_for_active_driver():
    class AliveDriver:
        session_id = "session-123"

        def execute_script(self, script):
            self.last_script = script
            return 1

    assert is_session_alive(AliveDriver()) is True


def test_is_session_alive_false_on_webdriver_exception():
    class DeadDriver:
        session_id = "session-dead"

        def execute_script(self, script):
            raise WebDriverException("boom")

    assert is_session_alive(DeadDriver()) is False


# === Testes unitários leves (mantidos) ===
def test_build_chrome_options_sets_headless_and_core_flags():
    opts = driver_module._build_chrome_options(headless=True)
    args = opts._arguments
    assert "--headless=new" in args
    assert "--no-sandbox" in args
    assert "--disable-dev-shm-usage" in args
    assert "--disable-blink-features=AutomationControlled" in args
    assert opts.page_load_strategy == "eager"


def test_build_chrome_options_respects_non_headless_mode():
    opts = driver_module._build_chrome_options(headless=False)
    args = opts._arguments
    assert "--headless=new" not in args


def test_is_remote_detects_selenium_hub_url(monkeypatch):
    monkeypatch.setenv("SELENIUM_HUB_URL", "http://localhost:4444")
    assert driver_module._is_remote() is True
    monkeypatch.delenv("SELENIUM_HUB_URL", raising=False)
    assert driver_module._is_remote() is False
