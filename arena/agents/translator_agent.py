from arena.config import DEFAULT_MODEL
from arena.services.prompt_builder import translation_messages


class TranslatorAgent:
    def __init__(self, provider, config, key):
        self.provider, self.config, self.key = provider, config, key

    async def translate(self, record, on_delta):
        return await self.provider.stream_complete(key=self.key, model=DEFAULT_MODEL, on_delta=on_delta,
            messages=translation_messages(self.config, record.source, record.target_language))

