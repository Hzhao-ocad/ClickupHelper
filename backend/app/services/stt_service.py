import logging

logger = logging.getLogger(__name__)


class STTService:
    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None

    def _load_model(self):
        if self.model is not None:
            return
        from faster_whisper import WhisperModel
        self.model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
        )

    def transcribe(self, audio_path: str, language: str | None = None) -> dict:
        """Transcribe audio to text.

        Args:
            audio_path: Path to the audio file.
            language: Language code (e.g. "zh", "en").  When *None* the model
                auto-detects the language, which works well for multilingual
                (Chinese / English) input.

        Returns:
            Dict with transcript, detected language, and duration.
        """
        self._load_model()
        segments, info = self.model.transcribe(
            audio_path,
            language=language,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )
        text = "".join(segment.text for segment in segments)
        return {
            "transcript": text.strip(),
            "language": info.language,
            "language_probability": round(info.language_probability, 2),
            "duration_ms": int(info.duration * 1000) if info.duration else 0,
        }
