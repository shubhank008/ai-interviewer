"""Compatibility exports for persistence and storage services.

New code should import concrete implementations from
``interviewer_domain.adapters.persistence``.
"""

from .adapters.persistence import *  # noqa: F401,F403
