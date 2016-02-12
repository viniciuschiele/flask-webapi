"""
Provides various decorators to set up the views.
"""


def authenticator(*args):
    """
    A decorator that apply a list of authenticators.

    :param args: A list of authenticators.
    :return: A function.
    """

    def decorator(func):
        func.authenticators = args
        return func
    return decorator


def permissions(*args):
    """
    A decorator that apply a list of permissions.

    :param args: A list of permissions.
    :return: A function.
    """

    def decorator(func):
        func.permissions = args
        return func
    return decorator


def content_negotiator(negotiator):
    """
    A decorator that apply a content negotiator.

    :param ContentNegotiatorBase negotiator: A class of content negotiator.
    :return: A function.
    """

    def decorator(func):
        func.content_negotiator = negotiator
        return func
    return decorator


def renderer(*args):
    """
    A decorator that apply a list of renderers.

    :param args: A list of renderers.
    :return: A function.
    """

    def decorator(func):
        func.renderers = args
        return func
    return decorator


def route(url, methods=None):
    """
    A decorator that is used to register a view function for a given URL rule.

    :param str url: The url rule.
    :param list methods: A list of http methods.
    :return: A function.
    """

    def decorator(func):
        func.url = url
        func.allowed_methods = methods
        return func
    return decorator


def serializer(schema, envelope=None):
    """
    A decorator that apply marshalling to the return values of your methods.

    :param Schema schema: The schema class to be used to serialize the values.
    :param str envelope: The key used to envelope the data.
    :return: A function.
    """

    def decorator(func):
        func.serializer = schema
        func.envelope = envelope
        return func
    return decorator


def error_handler(handler):
    """
    A decorator that apply error handling to an action or view.
    :param handler: A callable object.
    :return: A function.
    """

    def decorator(func):
        func.error_handler = handler
        return func
    return decorator
