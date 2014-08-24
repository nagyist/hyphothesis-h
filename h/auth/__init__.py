# -*- coding: utf-8 -*-
import jwt
from oauthlib import oauth2
from pyramid.authentication import SessionAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.exceptions import BadCSRFToken
from pyramid.session import check_csrf_token

from ..security import OpenID
from .grant_types import jwt_bearer
from .tokens import expires_in, token_generator, token_validator
from .utils import is_browser_client, is_equal, get_consumer


class ClientCredentialsValidator(oauth2.RequestValidator):
    def authenticate_client(self, request):
        client = get_consumer(request, request.client_id)

        if client is None:
            return False

        if request.client_secret:
            if not is_equal(client.client_secret, request.client_secret):
                return False

        # Require a CSRF token for the browser client.
        # TODO: Rename 'api.key' to something which reflects that it is used
        # by the browser client.
        if is_browser_client(request, client.client_id):
            if request.client_secret is None:
                try:
                    check_csrf_token(request, token='assertion')
                except BadCSRFToken:
                    return False

        request.client = client
        return True

    def get_default_scopes(self, client_id, request):
        # Besides the browser client, this grant type is only intended to
        # be used by backend applications. Therefore, it is given minimal
        # capabilities. TODO: revisit this after the browser client is
        # given its own keys and allow the operator to create keys for
        # backend services with more privileges.
        return []

    def save_bearer_token(self, token, request):
        pass

    def validate_bearer_token(self, token, scopes, request):
        if scopes != [OpenID]:
            return False
        request.client = get_consumer(request)
        return token_validator(request, token)

    def validate_grant_type(self, client_id, grant_type, client, request):
        return True

    def validate_scopes(self, client_id, scopes, client, request):
        if is_browser_client(request, client_id):
            return True
        else:
            return scopes == []


class JWTValidator(oauth2.RequestValidator):
    def get_default_scopes(self, client_id, request):
        return [OpenID]

    def get_original_scopes(self, token, request):
        return [OpenID]

    def validate_grant_type(self, client_id, grant_type, client, request):
        return True

    def validate_scopes(self, client_id, scopes, client, request):
        if scopes == [OpenID]:
            return True

    def validate_web_token(self, token, payload, request):
        """
        Validate a JWT Bearer Token.

        This is an extension to the request validator interface defined by
        OAuthLib. It may change when JWT Bearer Token support is merged
        upstream.
        """
        consumer = get_consumer(request, payload['iss'])

        if consumer is None:
            return False

        try:
            jwt.decode(token, consumer.client_secret)
        except jwt.DecodeError:
            return False

        audience = payload.get('aud')
        if audience != request.resource_url(request.root, 'api', 'token'):
            return False

        request.consumer = consumer
        request.user = payload['sub']
        return True


class OAuthPolicy(SessionAuthenticationPolicy):
    def unauthenticated_userid(self, request):
        if hasattr(request, 'user'):
            return request.user

        userid = super(OAuthPolicy, self).unauthenticated_userid(request)

        if userid is None:
            request.verify_request(scopes=[OpenID])
            request.user = getattr(request, 'user', None)
        else:
            request.user = userid

        return request.user


def includeme(config):
    config.include('pyramid_oauthlib')
    config.add_oauth_param('assertion')
    config.add_oauth_param('assertion_type')
    config.add_oauth_param('client_assertion')
    config.add_oauth_param('client_assertion_type')
    config.add_tween('h.auth.tokens.annotator_tween_factory')

    config.add_grant_type(jwt_bearer.JWTBearerGrant, jwt_bearer.JWT_BEARER,
                          request_validator=JWTValidator())
    config.add_grant_type(oauth2.ClientCredentialsGrant, 'client_credentials',
                          request_validator=ClientCredentialsValidator())
    config.add_token_type(oauth2.BearerToken,
                          request_validator=ClientCredentialsValidator(),
                          token_generator=token_generator,
                          expires_in=expires_in)

    # Configure the authentication policy
    authn_debug = config.registry.settings.get('debug_authorization')
    authn_policy = OAuthPolicy(debug=authn_debug, prefix='')
    config.set_authentication_policy(authn_policy)

    # Configure the authorization policy
    authz_policy = ACLAuthorizationPolicy()
    config.set_authorization_policy(authz_policy)

    # Add the default consumer as a property of the request.
    config.add_request_method(get_consumer, 'consumer', reify=True)
