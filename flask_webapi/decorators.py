def authenticator(*args):
    """
    A decorator that apply a list of authenticators.

    :param args: A list of authenticators.
    :return: A function.
    """

    def decorator(func):
        func._authenticators = args
        return func
    return decorator


def permissions(*args):
    """
    A decorator that apply a list of permissions.

    :param args: A list of permissions.
    :return: A function.
    """

    def decorator(func):
        func._permissions = args
        return func
    return decorator


def content_negotiator(negotiator):
    """
    A decorator that apply a content negotiator.

    :param negotiator: A class of content negotiator.
    :return: A function.
    """

    def decorator(func):
        func._content_negotiator = negotiator
        return func
    return decorator


def renderer(*args):
    """
    A decorator that apply a list of renderers.

    :param args: A list of renderers.
    :return: A function.
    """

    def decorator(func):
        func._renderers = args
        return func
    return decorator


def route(url, methods=None):
    """
    A decorator that is used to register a view function for a given URL rule.

    :param url: The url rule.
    :param methods: A list of http methods.
    :return: A function.
    """

    def decorator(func):
        func._url = url
        func._methods = methods
        return func
    return decorator


def serializer(schema, envelope=None):
    """
    A decorator that apply marshalling to the return values of your methods.

    :param schema: The schema class to be used to serialize the values.
    :param envelope: The key used to envelope the data.
    :return: A function.
    """

    def decorator(func):
        func._serializer = schema
        func._envelope = envelope
        return func
    return decorator

