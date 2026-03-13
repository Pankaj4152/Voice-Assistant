class SecurityLayer:
    """
    Basic security validation before executing actions
    """

    def __init__(self):

        # blocked keywords
        self.blocked_keywords = [
            "delete system32",
            "format disk",
            "shutdown forever",
            "remove system files"
        ]

    def check(self, parsed_intent):

        text = getattr(parsed_intent, "text", "").lower()

        for word in self.blocked_keywords:
            if word in text:
                return {
                    "allowed": False,
                    "reason": "Blocked dangerous command"
                }

        return {
            "allowed": True
        }