import pytest

from app.chat.messages import UIMessage, latest_user_message


def test_latest_user_message_joins_text_parts() -> None:
    message = latest_user_message(
        [
            UIMessage(role="assistant", parts=[{"type": "text", "text": "Hi"}]),
            UIMessage(
                id="message-1",
                role="user",
                parts=[
                    {"type": "text", "text": "Annual "},
                    {"type": "text", "text": "revenue"},
                ],
            ),
        ]
    )

    assert message.text() == "Annual revenue"


def test_latest_user_message_requires_non_empty_user_text() -> None:
    with pytest.raises(ValueError, match="non-empty user message"):
        latest_user_message(
            [UIMessage(role="user", parts=[{"type": "text", "text": "  "}])]
        )


def test_latest_user_message_ignores_prior_citation_data_parts() -> None:
    message = latest_user_message(
        [
            UIMessage(
                role="assistant",
                parts=[
                    {"type": "text", "text": "A grounded answer."},
                    {
                        "type": "data-citation",
                        "data": {"chunk_id": "chunk-1"},
                    },
                ],
            ),
            UIMessage(
                role="user",
                parts=[{"type": "text", "text": "What was gross margin?"}],
            ),
        ]
    )

    assert message.text() == "What was gross margin?"
