"""Shared utility functions."""

def mask_email(email: str | None) -> str:
    """
    Mask email untuk privacy. Format: ja***@gmail.com
    
    Rules:
    - Local part: show 2 huruf pertama + '***'
    - Domain: unchanged
    - Edge cases: 
        - None/empty → "(no email)"
        - Local < 2 huruf → ***@domain
        - No @ → entire string masked
    """
    if not email:
        return "(no email)"

    email = email.strip().lower()

    if "@" not in email:
        return "***"

    local, domain = email.split("@", 1)

    if len(local) <= 2:
        masked_local = "***"
    else:
        masked_local = f"{local[:2]}***"

    return f"{masked_local}@{domain}"