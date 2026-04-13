"""
Input schema for the cross-channel-dedup skill.

Imported by the Phase 2 loader via:
    from skills.cross_channel_dedup.input_schema import CrossChannelDedupInput
"""
from pydantic import BaseModel


class CrossChannelDedupInput(BaseModel):
    # TODO (Phase 4): Add fields once the dedup skill design is complete.
    # Expected fields: existing_transactions (list), new_transactions (list),
    # window_days (int, default 7)
    pass
