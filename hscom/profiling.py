import builtins

def _identity_profile(func):
    return func

profile = getattr(
    builtins,
    "profile",
    _identity_profile,
)