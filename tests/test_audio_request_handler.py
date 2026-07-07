import unittest
from types import SimpleNamespace
from unittest.mock import patch

from audio_request_handler import AudioRequestHandler


class AudioRequestHandlerTests(unittest.TestCase):
    def test_resolve_virtual_audio_device_by_regex(self):
        with patch("audio_request_handler.sc", create=True) as mock_sc:
            mock_sc.all_microphones.return_value = [
                SimpleNamespace(name="CABLE Output (VB-Audio Virtual Cable)"),
                SimpleNamespace(name="Speakers"),
            ]
            config = SimpleNamespace(
                SAMPLING=SimpleNamespace(SOURCE_REGEX=r"^CABLE Output \(VB-Audio Virtual Cable\)$")
            )

            resolved = AudioRequestHandler.resolve_virtual_audio_device(config)

            self.assertEqual(resolved, "CABLE Output (VB-Audio Virtual Cable)")

    def test_resolve_virtual_audio_device_fallback_to_source(self):
        with patch("audio_request_handler.sc", create=True) as mock_sc:
            mock_sc.all_microphones.return_value = [
                SimpleNamespace(name="USB Audio"),
            ]
            config = SimpleNamespace(
                SAMPLING=SimpleNamespace(SOURCE="USB Audio")
            )

            resolved = AudioRequestHandler.resolve_virtual_audio_device(config)

            self.assertEqual(resolved, "USB Audio")


if __name__ == "__main__":
    unittest.main()
