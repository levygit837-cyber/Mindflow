"""OAuth2 authentication module.

Provides OAuth2 authentication with PKCE (Proof Key for Code Exchange)
for secure authorization code flow, with CSRF protection via state parameter.

Supports multiple OAuth2 providers:
- GitHub
- Google
- MindFlow (future)
"""

from .service import OAuth2Service
from .pkce import generate_code_challenge, generate_code_verifier, generate_pkce_pair
from .state_manager import StateManager

__all__ = [
    "OAuth2Service",
    "generate_code_challenge",
    "generate_code_verifier",
    "generate_pkce_pair",
    "StateManager",
]
