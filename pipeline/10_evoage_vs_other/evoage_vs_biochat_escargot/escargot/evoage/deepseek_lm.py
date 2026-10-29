"""DeepSeek backend for Escargot, so all benchmarked tools share one model.

Escargot ships ollama / azuregpt / chatgpt backends. Its ChatGPT class builds an
OpenAI client with no base_url, so it cannot reach the OpenCode proxy as-is.
Rather than editing Escargot, this subclasses ChatGPT and swaps the class into
`language_models` before Escargot is constructed -- so both `escargot.lm` and
`escargot.memory` (which is bound to the lm at construction) use it.

Two things differ from plain OpenAI:

1. deepseek-v4-flash spends output tokens on internal reasoning, which returns
   empty content unless thinking is disabled -- same workaround as BioChatter.
2. The proxy serves chat but not embeddings, while Escargot's memory module
   needs them. Embeddings therefore come from local Ollama (nomic-embed-text,
   768-dim). If a Chroma collection was previously created at 1536 dimensions it
   must be deleted, or writes fail with a dimension mismatch.
"""

import json
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI

DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://opencode.ai/zen/go/v1")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.environ.get("ESCARGOT_EMBED_MODEL", "nomic-embed-text:latest")


def _read_key() -> str:
    """Read the DeepSeek key from the BioChatter .env so there is one copy."""
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key
    env_path = os.environ.get(
        "DEEPSEEK_ENV",
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "Biochatter", ".env",
        ),
    )
    try:
        from dotenv import dotenv_values

        return (dotenv_values(env_path).get("DEEPSEEK_API_KEY") or "").strip()
    except Exception:
        return ""


def build_config(neo4j: dict) -> dict:
    """Config dict for Escargot. The 'chatgpt' key is what selects this backend."""
    return {
        "chatgpt": {
            "model_id": DEEPSEEK_MODEL,
            "prompt_token_cost": 0.0,
            "response_token_cost": 0.0,
            "temperature": 0.0,
            "max_tokens": 4096,
            "stop": None,
            "organization": "",
            "api_key": _read_key(),
            "embedding_id": EMBED_MODEL,
        },
        "neo4j": neo4j,
    }


def install():
    """Swap DeepSeekLM in for Escargot's ChatGPT class.

    Must be called before constructing Escargot, since Escargot binds both its
    language model and its memory during __init__.
    """
    from escargot import language_models

    class DeepSeekLM(language_models.ChatGPT):
        def __init__(self, config, model_name: str = "chatgpt", cache: bool = False):
            super().__init__(config, model_name, cache)
            # ChatGPT.__init__ resolves the key as
            # os.getenv("OPENAI_API_KEY", config["api_key"]) -- the environment
            # WINS. Force the configured DeepSeek key back, so a stray
            # OPENAI_API_KEY in the shell can never be sent to this endpoint.
            configured = config[model_name]["api_key"]
            if configured:
                self.api_key = configured
            # Re-point the client at the OpenAI-compatible proxy.
            self.client = OpenAI(api_key=self.api_key, base_url=DEEPSEEK_BASE_URL)

        def _one(self, messages, temperature):
            return self.client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=self.max_tokens,
                n=1,
                stop=self.stop,
                extra_body={"thinking": {"type": "disabled"}},
            )

        def chat(self, messages, num_responses: int = 1):
            """Emulate n>1 with CONCURRENT n=1 calls.

            The OpenCode proxy rejects n>1 outright ("only n = 1 is supported"),
            but Escargot asks for several samples when branching its graph of
            thoughts. Issuing them sequentially would make one logical call cost
            k round-trips of latency -- an artefact of this proxy, not of
            Escargot -- so they are issued in parallel and the choices merged.
            Wall-clock cost is then roughly one call regardless of k.
            """
            if num_responses <= 1:
                response = self._one(messages, self.temperature)
                self._record_usage([response])
                return response

            # Vary temperature on the extra samples so branching explores
            # genuinely different thoughts rather than k copies of one.
            temperatures = [self.temperature] + [
                max(self.temperature, 0.7)
            ] * (num_responses - 1)

            responses: list = [None] * num_responses
            with ThreadPoolExecutor(max_workers=min(num_responses, 8)) as pool:
                futures = {
                    pool.submit(self._one, messages, temp): idx
                    for idx, temp in enumerate(temperatures)
                }
                for future in as_completed(futures):
                    idx = futures[future]
                    try:
                        responses[idx] = future.result()
                    except Exception as exc:  # noqa: BLE001
                        # One failed sample must not lose the others; Escargot
                        # can proceed with fewer branches.
                        self.logger.warning("sample %d failed: %s", idx, exc)

            done = [r for r in responses if r is not None]
            if not done:
                raise RuntimeError("all parallel samples failed")

            first = done[0]
            for extra in done[1:]:
                first.choices.extend(extra.choices)
            self._record_usage(done)
            return first

        def _record_usage(self, responses) -> None:
            for response in responses:
                usage = getattr(response, "usage", None)
                if usage:
                    self.prompt_tokens += usage.prompt_tokens
                    self.completion_tokens += usage.completion_tokens

        def get_embedding(self, text_to_embed):
            """Embeddings via local Ollama; the proxy does not serve them."""
            payload = json.dumps(
                {"model": EMBED_MODEL, "prompt": text_to_embed}
            ).encode()
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/embeddings",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read())["embedding"]

    language_models.ChatGPT = DeepSeekLM
    return DeepSeekLM
