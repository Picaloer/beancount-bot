"""
Output schema for the cross-channel-dedup skill.

Imported by the Phase 2 loader via:
    from skills.cross_channel_dedup.output_schema import CrossChannelDedupOutput
"""
from pydantic import BaseModel


class CrossChannelDedupOutput(BaseModel):
    # TODO (Phase 4): Add fields once the dedup skill design is complete.
    # Expected fields: suspected_pairs (list), window_count (int)
    pass
