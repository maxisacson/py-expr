from functools import wraps

TRACE = False

depth = 0


def trace(f):
    if not TRACE:
        return f

    @wraps(f)
    def wrapper(*args, **kwargs):
        global depth

        print(f"{'  '*depth}{f.__name__} <- {args} {kwargs}")
        depth += 1

        ret = f(*args, **kwargs)

        depth -= 1
        print(f"{'  '*depth}{f.__name__} -> {ret}")

        return ret

    return wrapper


class ExprError(BaseException):
    pass


class TokenError(ExprError):
    pass


class ParseError(ExprError):
    pass


class EvalError(ExprError):
    pass
