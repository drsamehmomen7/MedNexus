from backend.app.engines.openmed.engine import deidentify_text


class EngineManager:
    """
    Central manager responsible for selecting
    the appropriate AI engine for each task.
    """

    DEFAULT_ENGINE = "OpenMed"

    def deidentify(self, text: str):
        return deidentify_text(text)

    def get_engine_name(self) -> str:
        return self.DEFAULT_ENGINE

    def get_engine_version(self) -> str:
        # سيتم لاحقًا قراءتها آليًا من المحرك
        return "1.9.1"