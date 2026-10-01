import uuid


def new_id(prefix: str) -> str:
    """Short stable identifier, e.g. 'rfq-3f9a1c2b'. Never derived from display names."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"
