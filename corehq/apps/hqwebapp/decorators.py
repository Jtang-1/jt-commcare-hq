from collections import defaultdict
from functools import wraps

from corehq.apps.hqwebapp.utils.bootstrap import set_bootstrap_version5


def use_bootstrap5(view_func):
    """Use this decorator on the dispatch method of a TemplateView subclass
    to enable Boostrap 5 features for the included template.

    Example:
        @use_bootstrap5
        def dispatch(self, request, *args, **kwargs):
            return super().dispatch(request, *args, **kwargs)

    Or alternatively:
        @method_decorator(use_bootstrap5, name='dispatch')
        class MyViewClass(MyViewSubclass):
            ...
    """
    return get_wrapped_view(view_func, lambda r: set_bootstrap_version5())


def waf_allow(kind, hard_code_pattern=None):
    """
    Using this decorator simply registers a function for later use

    Since this is used to pull out metadata about our application,
    and not to modify the functioning of the application itself,
    there is no need to modify the function.

    Use this decorator like this

        @waf_allow('XSS_BODY')
        def my_view(...): ...

    to signify "if you put a WAF in front of this, make sure the XSS_BODY rule does not BLOCK this url pattern"

    For super abstracted setups where getting at the original view is hard
    you can use

        waf_allow('XSS_BODY', hard_code_pattern=r'/url/regex/')

    instead.
    """
    if hard_code_pattern:
        waf_allow.views[kind].add(hard_code_pattern)
        return

    def inner(fn):
        waf_allow.views[kind].add(fn)
        return fn
    return inner


waf_allow.views = defaultdict(set)


def set_request_flag(view_func, attr_name, attr_value=True):
    def _set_attr(request):
        setattr(request, attr_name, attr_value)

    return get_wrapped_view(view_func, _set_attr)


def get_wrapped_view(view_func, request_modifier):
    @wraps(view_func)
    def _wrapped(*args, **kwargs):
        request = _get_request_from_args(*args, **kwargs)
        request_modifier(request)
        return view_func(*args, **kwargs)

    return _wrapped


def _get_request_from_args(*args, **kwargs):
    if hasattr(args[0], 'META'):
        # function view
        return args[0]
    else:
        # class view
        return args[1]
