import collections

import pytest

from src.uploader_modular import TikTokUploader, ConfirmationStatus


@pytest.fixture(autouse=True)
def _speed_up_sleep(monkeypatch):
    monkeypatch.setattr("src.uploader_modular.time.sleep", lambda *args, **kwargs: None)


def test_post_video_instantiates_fresh_modules_each_run(monkeypatch):
    counts = collections.Counter()

    class FakeVideoUploadModule:
        def __init__(self, driver, logger):
            counts["upload"] += 1

        def navigate_to_upload_page(self, *args, **kwargs):
            return True

        def send_video_file(self, *args, **kwargs):
            return True

    class FakeDescriptionModule:
        def __init__(self, driver, logger):
            counts["description"] += 1

        def fill_description(self, *args, **kwargs):
            return True

        def _wait_visible(self, *args, **kwargs):  # legacy compatibility
            return True

    class FakeAudienceModule:
        def __init__(self, driver, logger):
            counts["audience"] += 1

        def set_public(self, *args, **kwargs):
            return True

    class FakePostActionModule:
        def __init__(self, driver, logger):
            counts["post_action"] += 1

        def click_publish_button(self, *args, **kwargs):
            return True

        def handle_confirmation_dialog(self, *args, **kwargs):
            return True

        def detect_content_violation(self):
            return False

        def is_on_upload_page(self):
            return False

        def _wait_clickable(self, *args, **kwargs):  # legacy compatibility
            return True

    class FakeConfirmationModule:
        def __init__(self, driver, logger):
            counts["confirmation"] += 1

        def mark_upload_screen_seen(self):
            counts["confirmation_mark"] += 1

        def confirm_posted(self, *args, **kwargs):
            class _Result:
                status = ConfirmationStatus.PUBLISHED

            return _Result()

        def wait_for_confirmation(self, *args, **kwargs):
            return True

        def get_post_status(self):
            return {}

        def print_status(self):
            return None

    class FakeDuplicateProtectionModule:
        def __init__(self, logger):
            counts["duplicate"] += 1

        def can_post_video(self, *args, **kwargs):
            return True, "ok"

        def create_posting_lock(self, *args, **kwargs):
            return True

        def remove_posting_lock(self, *args, **kwargs):
            counts["lock_release"] += 1
            return True

        def finalize_post_operation(self, *args, **kwargs):
            counts["finalize"] += 1
            return True

    monkeypatch.setattr("src.uploader_modular.VideoUploadModule", FakeVideoUploadModule)
    monkeypatch.setattr("src.uploader_modular.DescriptionModule", FakeDescriptionModule)
    monkeypatch.setattr("src.uploader_modular.AudienceModule", FakeAudienceModule)
    monkeypatch.setattr("src.uploader_modular.PostActionModule", FakePostActionModule)
    monkeypatch.setattr("src.uploader_modular.PostConfirmationModule", FakeConfirmationModule)
    monkeypatch.setattr("src.uploader_modular.DuplicateProtectionModule", FakeDuplicateProtectionModule)

    uploader = TikTokUploader(
        driver=object(),
        logger=lambda *args, **kwargs: None,
        account_name="acc-isolated",
    )

    assert uploader.post_video("/tmp/video.mp4", "desc")
    assert uploader.post_video("/tmp/video.mp4", "desc")

    assert counts["upload"] == 2
    assert counts["description"] == 2
    assert counts["audience"] == 2
    assert counts["post_action"] == 2
    assert counts["confirmation"] == 2
    assert counts["duplicate"] == 2
    assert counts["finalize"] == 2
