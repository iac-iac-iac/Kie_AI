import json

from kie_sidecar.kie.chat import ChatStreamer, StreamDelta, StreamDone


class FakeAsyncLines:
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    def __aiter__(self):
        self._index = 0
        return self

    async def __anext__(self):
        if self._index >= len(self._lines):
            raise StopAsyncIteration
        line = self._lines[self._index]
        self._index += 1
        return line


class FakeStreamResponse:
    status_code = 200

    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    def aiter_lines(self):
        return FakeAsyncLines(self._lines)


async def test_parse_openai_stream():
    lines = [
        'data: {"choices":[{"delta":{"content":"Hel"}}]}',
        'data: {"choices":[{"delta":{"content":"lo"}}]}',
        'data: {"usage":{"prompt_tokens":3,"completion_tokens":2},"credits_consumed":0.1}',
        "data: [DONE]",
    ]
    streamer = ChatStreamer(client=None)  # type: ignore[arg-type]
    events = []
    async for event in streamer._parse_openai_stream(FakeStreamResponse(lines)):
        events.append(event)

    assert any(isinstance(e, StreamDelta) and e.text == "Hel" for e in events)
    done = [e for e in events if isinstance(e, StreamDone)][0]
    assert done.text == "Hello"
    assert done.tokens_in == 3
    assert done.tokens_out == 2
    assert done.credits == 0.1


async def test_parse_claude_stream():
    lines = [
        "event: content_block_delta",
        f'data: {json.dumps({"delta": {"text": "Hi"}})}',
        "event: message_delta",
        f'data: {json.dumps({"usage": {"output_tokens": 4}})}',
    ]
    streamer = ChatStreamer(client=None)  # type: ignore[arg-type]
    events = []
    async for event in streamer._parse_claude_stream(FakeStreamResponse(lines)):
        events.append(event)

    assert any(isinstance(e, StreamDelta) and e.text == "Hi" for e in events)
    done = [e for e in events if isinstance(e, StreamDone)][0]
    assert done.text == "Hi"
    assert done.tokens_out == 4
