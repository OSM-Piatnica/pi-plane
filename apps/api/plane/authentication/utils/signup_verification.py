# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Email verification code for the email-and-password sign-up.

Before an account is created with an email and a password, the person proves they own the address by typing a
8-digit code sent to it. The code lives in Redis under its own key, apart from the one-time sign-in codes, so a
sign-in code cannot create an account with a password and the check works whether or not one-time sign-in is on.
The caps are the ones of the one-time sign-in codes: 5 wrong tries per code and 4 codes per address in 10 minutes.
"""

# Python imports
import json
import os
import secrets

# Module imports
from plane.authentication.adapter.error import AUTHENTICATION_ERROR_CODES, AuthenticationException
from plane.authentication.provider.credentials.one_time_code import OneTimeCodeProvider
from plane.license.utils.instance_value import get_configuration_value
from plane.settings.redis import redis_instance
from plane.utils.exception_logger import log_exception
from plane.utils.numeric_code import generate_numeric_code

KEY_PREFIX = "signup_verification_code_"
CODE_TTL_SECONDS = 600
MAX_VERIFY_ATTEMPTS = OneTimeCodeProvider.MAX_VERIFY_ATTEMPTS
MAX_CODES_PER_WINDOW = OneTimeCodeProvider.MAX_CODES_PER_WINDOW
ISSUE_WINDOW_SECONDS = OneTimeCodeProvider.ISSUE_WINDOW_SECONDS
_INCREMENT_COUNTER_SCRIPT = OneTimeCodeProvider.INCREMENT_COUNTER_SCRIPT
# Gives back one try, unless the counter is gone (a DECR on a missing key would leave a counter without an expiry)
_GIVE_BACK_TRY_SCRIPT = 'if redis.call("EXISTS", KEYS[1]) == 1 then return redis.call("DECR", KEYS[1]) end return 0'


def is_signup_email_verification_required():
    """The code is asked for when the check is on (ENABLE_SIGNUP_EMAIL_VERIFICATION, default on) and SMTP is set up.

    Without SMTP no code can reach anyone, so sign-up works as before rather than being impossible.
    """
    (ENABLE_SIGNUP_EMAIL_VERIFICATION, EMAIL_HOST) = get_configuration_value(
        [
            {
                "key": "ENABLE_SIGNUP_EMAIL_VERIFICATION",
                "default": os.environ.get("ENABLE_SIGNUP_EMAIL_VERIFICATION", "1"),
            },
            {"key": "EMAIL_HOST", "default": os.environ.get("EMAIL_HOST")},
        ]
    )
    return ENABLE_SIGNUP_EMAIL_VERIFICATION != "0" and bool(EMAIL_HOST)


def _error(name, email):
    return AuthenticationException(
        error_code=AUTHENTICATION_ERROR_CODES[name],
        error_message=name,
        payload={"email": email},
    )


class SignUpEmailVerification:
    def __init__(self, email):
        self.email = email
        self.key = f"{KEY_PREFIX}{email}"
        self.attempts_key = f"{self.key}:verify_attempts"
        self.issued_key = f"{self.key}:issued"

    def issue(self):
        """Store a new code for the address and return it; raises once too many codes were asked for."""
        ri = redis_instance()
        issued = int(ri.eval(_INCREMENT_COUNTER_SCRIPT, 1, self.issued_key, ISSUE_WINDOW_SECONDS))
        if issued > MAX_CODES_PER_WINDOW:
            raise _error("SIGN_UP_VERIFICATION_CODE_ATTEMPT_EXHAUSTED", self.email)

        code = generate_numeric_code()
        # One transaction: a try counted between the two steps would otherwise be wiped against the new code, or the
        # new code compared with the old budget. A new code starts with a fresh budget of wrong tries.
        with ri.pipeline(transaction=True) as pipe:
            pipe.set(self.key, json.dumps({"email": self.email, "code": code}), ex=CODE_TTL_SECONDS)
            pipe.delete(self.attempts_key)
            pipe.execute()
        return code

    def verify(self, code):
        """Check the code; raises when it is missing, wrong, expired or tried too often.

        The code is kept on success, and that try is not counted, until consume(): an account that still fails to be
        created (a weak password, say) can be retried with the same code.
        """
        code = str(code or "").strip()
        if not code:
            raise _error("SIGN_UP_VERIFICATION_CODE_REQUIRED", self.email)

        ri = redis_instance()
        if not ri.exists(self.key):
            raise _error("EXPIRED_SIGN_UP_VERIFICATION_CODE", self.email)

        # Count the try before comparing, so no more than MAX_VERIFY_ATTEMPTS codes are compared, even in parallel.
        # The counter expires with the code; EXPIRE 0 would delete it at once, hence at least 1 second.
        remaining_ttl = ri.ttl(self.key)
        if remaining_ttl is None or remaining_ttl <= 0:
            remaining_ttl = 1
        attempts = int(ri.eval(_INCREMENT_COUNTER_SCRIPT, 1, self.attempts_key, remaining_ttl))

        raw = ri.get(self.key)
        if raw is None:
            raise _error("EXPIRED_SIGN_UP_VERIFICATION_CODE", self.email)
        if attempts <= MAX_VERIFY_ATTEMPTS and secrets.compare_digest(str(json.loads(raw)["code"]), code):
            # Only wrong codes use up the budget: the code is kept for retries (a weak password, say), and five of
            # those must not lock out somebody who typed it right every time.
            ri.eval(_GIVE_BACK_TRY_SCRIPT, 1, self.attempts_key)
            return

        if attempts >= MAX_VERIFY_ATTEMPTS:
            # Drop the code; a new one has to be asked for, which the issued-code counter caps.
            ri.delete(self.key, self.attempts_key)
            raise _error("SIGN_UP_VERIFICATION_CODE_ATTEMPT_EXHAUSTED", self.email)
        raise _error("INVALID_SIGN_UP_VERIFICATION_CODE", self.email)

    def consume(self):
        """Remove the code and its try counter once the account exists.

        The issued-code counter stays until its window ends, so the cap on codes per address cannot be reset. The
        account exists by now, so a Redis error here is logged and does not stop the person from signing in: the code
        is of no use to anybody once the address has an account, and expires on its own.
        """
        try:
            redis_instance().delete(self.key, self.attempts_key)
        except Exception as e:
            log_exception(e)
