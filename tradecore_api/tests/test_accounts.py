"""Sign-up, login and account lookup."""

from django.urls import reverse
from rest_framework import status

from tradecore_api.models import User
from tradecore_api.tests.base import APITestCaseWithAuth
from tradecore_api.tests.factories import DEFAULT_PASSWORD


class SignUpTests(APITestCaseWithAuth):
    """POST /api/signup."""

    url = reverse("signup")

    def valid_payload(self, **overrides):
        payload = {
            "email": "New.User@Example.com",
            "password": "corrective-horse-72",
            "first_name": "New",
            "last_name": "User",
        }
        payload.update(overrides)
        return payload

    def test_signup_succeeds_with_no_provider_keys(self):
        """Registration must work on a clone with no third-party keys."""
        response = self.client.post(self.url, self.valid_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)

    def test_signup_returns_a_usable_token(self):
        response = self.client.post(self.url, self.valid_payload(), format="json")
        token = response.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"JWT {token}")
        me = self.client.get(reverse("me"))
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data["user"]["email"], "new.user@example.com")

    def test_signup_lowercases_the_email(self):
        self.client.post(self.url, self.valid_payload(), format="json")
        self.assertTrue(User.objects.filter(email="new.user@example.com").exists())

    def test_signup_hashes_the_password(self):
        payload = self.valid_payload()
        self.client.post(self.url, payload, format="json")
        user = User.objects.get(email="new.user@example.com")
        self.assertNotEqual(user.password, payload["password"])
        self.assertTrue(user.check_password(payload["password"]))

    def test_signup_accepts_form_encoding(self):
        """A form-encoded body must not be treated as an immutable QueryDict."""
        response = self.client.post(self.url, self.valid_payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_signup_rejects_a_duplicate_email(self):
        self.client.post(self.url, self.valid_payload(), format="json")
        response = self.client.post(self.url, self.valid_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data["error"]["fields"])

    def test_signup_rejects_a_weak_password(self):
        response = self.client.post(self.url, self.valid_payload(password="123"), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data["error"]["fields"])

    def test_signup_rejects_a_malformed_email(self):
        response = self.client.post(
            self.url, self.valid_payload(email="not-an-email"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signup_never_echoes_the_password(self):
        response = self.client.post(self.url, self.valid_payload(), format="json")
        self.assertNotIn("password", response.data["user"])


class LoginTests(APITestCaseWithAuth):
    """POST /api/login."""

    url = reverse("login")

    def test_login_with_valid_credentials(self):
        user = self.make_user()
        response = self.client.post(
            self.url,
            {"email": user.email, "password": DEFAULT_PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertIn("refresh", response.data)

    def test_login_with_a_wrong_password(self):
        user = self.make_user()
        response = self.client.post(
            self.url, {"email": user.email, "password": "wrong"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_with_an_unknown_email_looks_identical(self):
        """Login must not reveal whether an address is registered."""
        user = self.make_user()
        wrong_password = self.client.post(
            self.url, {"email": user.email, "password": "wrong"}, format="json"
        )
        unknown_email = self.client.post(
            self.url, {"email": "nobody@example.com", "password": "wrong"}, format="json"
        )
        self.assertEqual(wrong_password.status_code, unknown_email.status_code)
        self.assertEqual(wrong_password.data, unknown_email.data)

    def test_login_with_missing_params(self):
        response = self.client.post(self.url, {"user": "abc"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_is_case_insensitive_on_the_email(self):
        user = self.make_user(email="mixed.case@example.com")
        response = self.client.post(
            self.url,
            {"email": "Mixed.Case@Example.com", "password": DEFAULT_PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["id"], user.id)


class UserLookupTests(APITestCaseWithAuth):
    """GET /api/user/<id> and GET /api/me."""

    def test_user_lookup_requires_authentication(self):
        user = self.make_user()
        response = self.client.get(reverse("user", args=[user.id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_another_account_does_not_expose_its_geolocation(self):
        """Location is derived from someone's IP -- it is not public."""
        other = self.make_user(geolocation_data={"city": "Oslo"})
        self.authenticate(self.make_user())
        response = self.client.get(reverse("user", args=[other.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("geolocation_data", response.data["user"])

    def test_own_record_does_include_geolocation(self):
        user = self.authenticate(self.make_user(geolocation_data={"city": "Oslo"}))
        response = self.client.get(reverse("user", args=[user.id]))
        self.assertEqual(response.data["user"]["geolocation_data"], {"city": "Oslo"})

    def test_unknown_user_is_a_404(self):
        self.authenticate(self.make_user())
        response = self.client.get(reverse("user", args=[999999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_me_returns_the_token_owner(self):
        user = self.authenticate(self.make_user())
        response = self.client.get(reverse("me"))
        self.assertEqual(response.data["user"]["id"], user.id)


class TokenTests(APITestCaseWithAuth):
    """Token handling."""

    def test_a_garbage_token_is_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION="JWT not-a-real-token")
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_an_unsigned_none_algorithm_token_is_rejected(self):
        """A token with alg=none and no signature must never authenticate."""
        import base64
        import json

        def segment(data: dict) -> str:
            raw = json.dumps(data).encode()
            return base64.urlsafe_b64encode(raw).decode().rstrip("=")

        user = self.make_user()
        forged = (
            f"{segment({'alg': 'none', 'typ': 'JWT'})}."
            f"{segment({'user_id': user.id, 'token_type': 'access'})}."
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"JWT {forged}")
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_bearer_scheme_is_also_accepted(self):
        from tradecore_api.tokens import issue_tokens

        user = self.make_user()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_tokens(user)['token']}")
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_refresh_returns_a_new_access_token(self):
        from tradecore_api.tokens import issue_tokens

        user = self.make_user()
        refresh = issue_tokens(user)["refresh"]
        response = self.client.post(
            reverse("token-refresh"), {"refresh": refresh}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
