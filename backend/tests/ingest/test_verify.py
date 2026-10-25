from ingest.verify import _document_errors, _vector_length


def test_vector_length_supports_supabase_vector_formats() -> None:
    assert _vector_length([0.1, 0.2, 0.3]) == 3
    assert _vector_length("[0.1,0.2,0.3]") == 3
    assert _vector_length(None) == 0


def test_document_errors_accept_complete_contiguous_chunks(monkeypatch) -> None:
    monkeypatch.setattr("ingest.verify.settings.gemini_embedding_dimensions", 3)
    document = {"metadata": {"ingestion_status": "complete", "expected_chunk_count": 2}}
    chunks = [
        {
            "chunk_index": index,
            "content": "text",
            "embedding": [0.1, 0.2, 0.3],
            "search_vector": "'text':1",
        }
        for index in range(2)
    ]

    assert _document_errors(document, chunks) == []


def test_document_errors_reject_unicode_replacement_characters(monkeypatch) -> None:
    monkeypatch.setattr("ingest.verify.settings.gemini_embedding_dimensions", 1)
    document = {"metadata": {"ingestion_status": "complete", "expected_chunk_count": 1}}
    chunks = [
        {
            "chunk_index": 0,
            "content": "Company\ufffds revenue",
            "embedding": [0.1],
            "search_vector": "'revenue':1",
        }
    ]

    assert (
        "one or more chunks contain Unicode replacement characters"
        in _document_errors(document, chunks)
    )
