"""Auth middleware constants.

Full route protection is dependency-based in Slice 14 so health/readiness remain
public. Later slices can add route groups or middleware policies without changing
the principal shape.
"""

AUTH_PRINCIPAL_STATE_KEY = "principal"
