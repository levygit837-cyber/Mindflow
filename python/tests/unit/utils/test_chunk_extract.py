from mindflow_backend.runtime.chunk_extract import extract_chunk_parts


class _DummyChunk:
    def __init__(self, content):
        self.content = content


def test_extract_chunk_parts_reads_thinking_and_text_from_list_content() -> None:
    chunk = _DummyChunk(
        content=[
            {"type": "thinking", "thinking": "chain of thought"},
            {"type": "text", "text": "final answer"},
        ]
    )

    thought, texts = extract_chunk_parts(chunk)
    assert "chain of thought" in thought
    assert texts == ["final answer"]
