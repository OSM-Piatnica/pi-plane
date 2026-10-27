# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import uuid

# Django import
from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

# Module imports
from plane.authentication.adapter.error import AUTHENTICATION_ERROR_CODES, AuthenticationException
from plane.authentication.provider.oidc.adapter import SESSION_SURFACE, OidcProvider
from plane.authentication.provider.oidc.registry import get_provider_spec
from plane.authentication.utils.host import base_host
from plane.authentication.utils.login import user_login
from plane.authentication.utils.oauth_state import validate_oauth_state
from plane.authentication.utils.redirection_path import get_redirection_path
from plane.authentication.utils.user_auth_workflow import post_user_auth_workflow
from plane.license.models import Instance
from plane.utils.path_validator import get_allowed_hosts, get_safe_redirect_url, validate_next_path


def _error_redirect(request, exc, next_path, is_space):
    url = get_safe_redirect_url(
        base_url=base_host(request=request, is_space=is_space, is_app=not is_space),
        next_path=next_path,
        params=exc.get_error_dict(),
    )
    return HttpResponseRedirect(url)


def _exception(code):
    return AuthenticationException(error_code=AUTHENTICATION_ERROR_CODES[code], error_message=code)


class OidcInitiateEndpoint(View):
    """Sends the browser to the provider. The same view serves the app and the spaces (``is_space``)."""

    is_space = False

    def get(self, request, provider):
        is_space = self.is_space
        request.session["host"] = base_host(request=request, is_space=is_space, is_app=not is_space)
        request.session[SESSION_SURFACE] = "space" if is_space else "app"
        next_path = request.GET.get("next_path")
        if next_path:
            request.session["next_path"] = str(next_path)

        instance = Instance.objects.first()
        if instance is None or not instance.is_setup_done:
            return _error_redirect(request, _exception("INSTANCE_NOT_CONFIGURED"), next_path, is_space)

        spec = get_provider_spec(provider)
        try:
            if spec is None:
                raise _exception("OIDC_NOT_CONFIGURED")
            state = uuid.uuid4().hex
            adapter = OidcProvider(request=request, spec=spec, state=state)
            auth_url = adapter.get_auth_url()
            request.session["state"] = state
            return HttpResponseRedirect(auth_url)
        except AuthenticationException as e:
            return _error_redirect(request, e, next_path, is_space)


class OidcSpaceInitiateEndpoint(OidcInitiateEndpoint):
    is_space = True


class OidcCallbackEndpoint(View):
    """The one redirect URI of a provider, for the app and for the spaces alike."""

    def get(self, request, provider):
        is_space = request.session.get(SESSION_SURFACE) == "space"
        next_path = request.session.get("next_path")
        spec = get_provider_spec(provider)
        code = request.GET.get("code")
        state = request.GET.get("state")

        if (
            spec is None
            or request.GET.get("error")
            or not code
            or not validate_oauth_state(request=request, state=state)
        ):
            return _error_redirect(request, _exception("OIDC_PROVIDER_ERROR"), next_path, is_space)

        try:
            adapter = OidcProvider(
                request=request, spec=spec, code=code, callback=None if is_space else post_user_auth_workflow
            )
            user = adapter.authenticate()
            user_login(request=request, user=user, is_app=not is_space, is_space=is_space)
        except AuthenticationException as e:
            return _error_redirect(request, e, next_path, is_space)

        if is_space:
            next_path = validate_next_path(next_path=next_path)
            url = f"{base_host(request=request, is_space=True).rstrip('/')}{next_path}"
            if url_has_allowed_host_and_scheme(url, allowed_hosts=get_allowed_hosts()):
                return HttpResponseRedirect(url)
            return HttpResponseRedirect(base_host(request=request, is_space=True))
        path = next_path or get_redirection_path(user=user)
        url = get_safe_redirect_url(base_url=base_host(request=request, is_app=True), next_path=path, params={})
        return HttpResponseRedirect(url)
