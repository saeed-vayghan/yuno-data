"""Privacy helpers: the full customer ID never leaves core."""

MASK = "••••"


def mask_id(customer_id: str | None) -> str | None:
    """'cus_8f2a91c07f3a' -> 'cus_••••7f3a'; None -> None."""
    if customer_id is None:
        return None
    prefix, _, token = customer_id.rpartition("_")
    head = f"{prefix}_" if prefix else ""
    return f"{head}{MASK}{token[-4:]}"
