"""Token issuance, in one place.

The previous implementation signed tokens by hand with a second secret that
was separate from Django's own, while the REST framework was configured to
verify them with SimpleJWT -- the two never agreed.  Issuing and verifying now
both go through SimpleJWT and one signing key.
"""

from rest_framework_simplejwt.tokens import RefreshToken

from tradecore_api.models import User


def issue_tokens(user: User) -> dict[str, str]:
    """Return an access/refresh pair for ``user``.

    ``token`` duplicates ``access`` so that the header format this API has
    always documented -- ``Authorization: JWT <token>`` -- keeps working.
    """
    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)
    return {"token": access, "access": access, "refresh": str(refresh)}
