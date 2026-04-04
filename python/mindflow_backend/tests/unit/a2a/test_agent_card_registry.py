from mindflow_backend.communication.a2a.agent_card_registry import AgentCardRegistry
from mindflow_backend.schemas.a2a.agent_card import AgentCard

def test_agent_card_registry_generates_cards():
    # Act
    cards = AgentCardRegistry.get_agent_cards()

    # Assert
    assert isinstance(cards, list)
    assert len(cards) > 0 # Must have returned some agents
    
    first_card = cards[0]
    assert isinstance(first_card, AgentCard)
    
    assert "MindFlow" in first_card.name
    assert "https://api.mindflow.local/a2a" in first_card.url
    
    assert len(first_card.skills) >= 1
    assert first_card.skills[0].id is not None
