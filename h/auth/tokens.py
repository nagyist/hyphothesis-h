# -*- coding: utf-8 -*-
from annotator import auth

from .utils import get_consumer


def annotator_tween_factory(handler, registry):
    def annotator_tween(request):
        if 'X-Annotator-Auth-Token' in request.headers:
            token = request.headers['X-Annotator-Auth-Token']
            request.authorization = ('Bearer', token)
        return handler(request)
    return annotator_tween


def expires_in(request):
    return request.client.ttl


def token_generator(request):
    client = get_consumer(request)
    consumer = request.consumer
    credentials = request.extra_credentials or {}
    credentials['consumerKey'] = consumer.client_id
    credentials['ttl'] = consumer.ttl
    if request.user is not None:
        credentials['userId'] = request.user
    return auth.encode_token(credentials, client.client_secret)


def token_validator(request, token):
    if token is None:
        return False

    client = get_consumer(request)

    if client is None:
        return False

    try:
        token = auth.decode_token(token, client.client_secret, client.ttl)
    except auth.TokenInvalid:
        return False

    request.consumer = get_consumer(request, token.get('consumerKey'))
    request.user = token.get('userId')

    return True
