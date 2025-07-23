def suggest_actions(query: str, answer: str) -> list[dict]:
    """
    Suggests relevant actions based on the query and the generated answer.
    """
    suggested = []

    # Define a simple mapping of keywords to actions
    action_map = {
        "contact": {"description": "Visit our Contact Us page", "url": "https://example.com/contact"},
        "support": {"description": "Get technical support", "url": "https://example.com/support"},
        "pricing": {"description": "View pricing plans", "url": "https://example.com/pricing"},
        "download_report": {"description": "Download the latest annual report",
                            "url": "https://example.com/reports/latest.pdf"},
        "register": {"description": "Register for an account", "url": "https://example.com/register"},
        "sign_up": {"description": "Sign up for our newsletter", "url": "https://example.com/newsletter"},
        "features": {"description": "Explore product features", "url": "https://example.com/features"},
        "about_us": {"description": "Learn more About Us", "url": "https://example.com/about"}
    }

    # Combine query and answer for keyword matching
    search_text = (query + " " + answer).lower()

    for keyword, action_info in action_map.items():
        if keyword in search_text:
            # Check for duplicates before adding
            if action_info not in suggested:
                suggested.append(action_info)

    return suggested
