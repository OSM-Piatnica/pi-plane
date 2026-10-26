# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
# See the LICENSE file for details.

from django.urls import path

from .views import (
    CSRFTokenEndpoint,
    ForgotPasswordEndpoint,
    SetUserPasswordEndpoint,
    ResetPasswordEndpoint,
    ChangePasswordEndpoint,
    # App
    EmailCheckEndpoint,
    GitLabCallbackEndpoint,
    GitLabOauthInitiateEndpoint,
    GitHubCallbackEndpoint,
    GitHubOauthInitiateEndpoint,
    OneTimeCodeGenerateEndpoint,
    OneTimeCodeSignInEndpoint,
    OneTimeCodeSignUpEndpoint,
    SignInAuthEndpoint,
    SignOutAuthEndpoint,
    SignUpAuthEndpoint,
    ForgotPasswordSpaceEndpoint,
    ResetPasswordSpaceEndpoint,
    # Space
    EmailCheckSpaceEndpoint,
    GitLabCallbackSpaceEndpoint,
    GitLabOauthInitiateSpaceEndpoint,
    GitHubCallbackSpaceEndpoint,
    GitHubOauthInitiateSpaceEndpoint,
    OneTimeCodeGenerateSpaceEndpoint,
    OneTimeCodeSignInSpaceEndpoint,
    OneTimeCodeSignUpSpaceEndpoint,
    SignInAuthSpaceEndpoint,
    SignUpAuthSpaceEndpoint,
    SignOutAuthSpaceEndpoint,
    GiteaCallbackEndpoint,
    GiteaOauthInitiateEndpoint,
    GiteaCallbackSpaceEndpoint,
    GiteaOauthInitiateSpaceEndpoint,
    OidcCallbackEndpoint,
    OidcInitiateEndpoint,
    OidcSpaceInitiateEndpoint,
)

urlpatterns = [
    # credentials
    path("sign-in/", SignInAuthEndpoint.as_view(), name="sign-in"),
    path("sign-up/", SignUpAuthEndpoint.as_view(), name="sign-up"),
    path("spaces/sign-in/", SignInAuthSpaceEndpoint.as_view(), name="space-sign-in"),
    path("spaces/sign-up/", SignUpAuthSpaceEndpoint.as_view(), name="space-sign-up"),
    # signout
    path("sign-out/", SignOutAuthEndpoint.as_view(), name="sign-out"),
    path("spaces/sign-out/", SignOutAuthSpaceEndpoint.as_view(), name="space-sign-out"),
    # csrf token
    path("get-csrf-token/", CSRFTokenEndpoint.as_view(), name="get_csrf_token"),
    # One-time code sign in
    path("magic-generate/", OneTimeCodeGenerateEndpoint.as_view(), name="magic-generate"),
    path("magic-sign-in/", OneTimeCodeSignInEndpoint.as_view(), name="magic-sign-in"),
    path("magic-sign-up/", OneTimeCodeSignUpEndpoint.as_view(), name="magic-sign-up"),
    path(
        "spaces/magic-generate/",
        OneTimeCodeGenerateSpaceEndpoint.as_view(),
        name="space-magic-generate",
    ),
    path(
        "spaces/magic-sign-in/",
        OneTimeCodeSignInSpaceEndpoint.as_view(),
        name="space-magic-sign-in",
    ),
    path(
        "spaces/magic-sign-up/",
        OneTimeCodeSignUpSpaceEndpoint.as_view(),
        name="space-magic-sign-up",
    ),
    ## Github Oauth
    path("github/", GitHubOauthInitiateEndpoint.as_view(), name="github-initiate"),
    path("github/callback/", GitHubCallbackEndpoint.as_view(), name="github-callback"),
    path(
        "spaces/github/",
        GitHubOauthInitiateSpaceEndpoint.as_view(),
        name="space-github-initiate",
    ),
    path(
        "spaces/github/callback/",
        GitHubCallbackSpaceEndpoint.as_view(),
        name="space-github-callback",
    ),
    ## Gitlab Oauth
    path("gitlab/", GitLabOauthInitiateEndpoint.as_view(), name="gitlab-initiate"),
    path("gitlab/callback/", GitLabCallbackEndpoint.as_view(), name="gitlab-callback"),
    path(
        "spaces/gitlab/",
        GitLabOauthInitiateSpaceEndpoint.as_view(),
        name="space-gitlab-initiate",
    ),
    path(
        "spaces/gitlab/callback/",
        GitLabCallbackSpaceEndpoint.as_view(),
        name="space-gitlab-callback",
    ),
    # Email Check
    path("email-check/", EmailCheckEndpoint.as_view(), name="email-check"),
    path("spaces/email-check/", EmailCheckSpaceEndpoint.as_view(), name="email-check"),
    # Password
    path("forgot-password/", ForgotPasswordEndpoint.as_view(), name="forgot-password"),
    path(
        "reset-password/<uidb64>/<token>/",
        ResetPasswordEndpoint.as_view(),
        name="forgot-password",
    ),
    path(
        "spaces/forgot-password/",
        ForgotPasswordSpaceEndpoint.as_view(),
        name="space-forgot-password",
    ),
    path(
        "spaces/reset-password/<uidb64>/<token>/",
        ResetPasswordSpaceEndpoint.as_view(),
        name="space-forgot-password",
    ),
    path("change-password/", ChangePasswordEndpoint.as_view(), name="forgot-password"),
    path("set-password/", SetUserPasswordEndpoint.as_view(), name="set-password"),
    ## OpenID Connect single sign-on (Microsoft Entra, any OIDC provider), see provider/oidc/registry.py
    path("oidc/<slug:provider>/", OidcInitiateEndpoint.as_view(), name="oidc-initiate"),
    path("oidc/<slug:provider>/callback/", OidcCallbackEndpoint.as_view(), name="oidc-callback"),
    path("spaces/oidc/<slug:provider>/", OidcSpaceInitiateEndpoint.as_view(), name="space-oidc-initiate"),
    ## Gitea Oauth
    path("gitea/", GiteaOauthInitiateEndpoint.as_view(), name="gitea-initiate"),
    path("gitea/callback/", GiteaCallbackEndpoint.as_view(), name="gitea-callback"),
    path(
        "spaces/gitea/",
        GiteaOauthInitiateSpaceEndpoint.as_view(),
        name="space-gitea-initiate",
    ),
    path(
        "spaces/gitea/callback/",
        GiteaCallbackSpaceEndpoint.as_view(),
        name="space-gitea-callback",
    ),
]
