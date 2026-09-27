class BayMEMCError(Exception):
    """Base exception for the package."""


class NotEstimableError(BayMEMCError):
    """Raised when local support is insufficient and inference must abstain."""


class AuthorityError(BayMEMCError):
    """Raised when an action lacks constitutional authority."""


class ConstitutionalViolation(BayMEMCError):
    """Raised when an action would reduce the protected rights floor."""


class IntegrityError(BayMEMCError):
    """Raised when hashes, ledgers, freezes, or signatures do not verify."""


class ConsentError(BayMEMCError):
    """Raised when sensitive data are accessed without a valid receipt."""
