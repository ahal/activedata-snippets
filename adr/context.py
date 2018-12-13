import ast
import inspect
from jsone.interpreter import ExpressionEvaluator
from jsone.prattparser import prefix

COMMON_CONTEXTS = {
    'attribute': {'nargs': '?',
                  'default': None,
                  'help': "Display values of specified attribute within --table."},
    'branch': [['-B', '--branch'],
               {'default': 'mozilla-central',
                'help': "Branches to query results from",
                }],
    'build_type': [['-b', '--build-type'],
                   {'default': 'opt',
                    'help': "Build type (default: opt)",
                    }],
    'format': [['--format'],
               {'type': str,
                'default': 'table',
                'help': "format of result"
                }],
    'from_date': [['--from'],
                  {'default': 'today-week',
                   'help': "Starting date to pull data from, defaults "
                           "to a week ago",
                   }],
    'groupby': [['--groupby'], {'default': 'result.test'}],
    'path': [['--path'],
             {'default': 'dom/indexedDB',
              'help': "Path relative to repository root (file or directory)",
              }],
    'platform': [['-p', '--platform'],
                 {'default': 'windows10-64',
                  'help': "Platform to limit results to (default: windows10-64)",
                  }],
    'platform_config': [['--platform-config'], {'default': 'test-'}],
    'limit': [['--limit'],
              {'type': int,
               'default': 10,
               'help': "limit the number of rows in result"
               }],

    'rev': [['-r', '--revision'],
            {'default': '5b33b070378a',
             'help': "Revision to limit results to",
             }],
    'result': [['--result'], {'default': "F"}],
    'sort_key': [['--sort-key'],
                 {'type': int,
                  'default': 4,
                  'help': "Key to sort on (int, 0-based index)",
                  }],
    'table': [['--table'],
              {'default': None,
               'help': "Table to inspect."}],
    'test_name': [['-t', '--test'],
                  {'default': '',
                   'help': "Path to a test file",
                   }],
    'to_date': [['--to'],
                {'default': 'eod',  # end of day
                 'help': "Ending date to pull data from, defaults "
                         "to now",
                 }],
}
"""
These are commonly used arguments which can be re-used. They are shared to
provide a consistent CLI across recipes/queries. Ordered by alphabet.
"""


class ContextExtractor(ExpressionEvaluator):
    """
    Context extractor is used in conjunction with extract_context_names
    to extract argument context as a token value
    """

    def __init__(self):
        # Init evaluator with fake empty context
        super(ContextExtractor, self).__init__({})
        self.infix_rules = super(ContextExtractor, self).infix_rules
        for k, v in super(ContextExtractor, self).prefix_rules.items():
            self.prefix_rules.setdefault(k, v)
        # Init empty context set
        self.contexts = set()

    @prefix("identifier")
    def identifier(self, token, pc):
        """
        Get corresponding value for token
        In this function, we return the same token value without using context
        Args:
            token: token object
            pc: parse context

        Returns: same token value

        """
        self.contexts.add(token.value)
        return token.value

    def parse(self, expression):
        """
        Parse current expression, return contexts inside this expression
        Args:
            expression (str): expression

        Returns:
            set of contexts

        """
        self.contexts.clear()
        super(ContextExtractor, self).parse(expression)
        return self.contexts


G_ZEROCONTEXT_EVALUATOR = ContextExtractor()


def extract_context_names(query):
    """
    Extract contexts list from query object
    This is to mimic json-e render() function
    Given using only $eval in query
    Args:
        query (dict): query object to extract context

    Returns:
        contexts (set): set of context names

    """
    contexts = set()
    if isinstance(query, dict):
        for k, v in query.items():
            if k == "$eval":
                contexts.update(G_ZEROCONTEXT_EVALUATOR.parse(v))
            else:
                contexts.update(extract_context_names(v))
    elif isinstance(query, list):
        for v in query:
            contexts.update(extract_context_names(v))

    return contexts


def get_context_definitions(definitions, specific_defs={}):
    """
    Build full context definitions from list of contexts with pre-defined definitions

    Args:
        definitions (list): mixed array of string and context definitions
        specific_defs (dict): specific definitions of contexts not in COMMON_CONTEXTS

    Returns:
        result (dict): a full dictionary of context definitions,
     each context definition has a name as key and attributes as value
    """

    result = {}

    for item in definitions:
        if isinstance(item, dict):
            result.update(item)
        elif isinstance(item, str):
            # if an item appears in both specific_defs and COMMON_CONTEXT,
            # get from specific_defs
            if item in specific_defs:
                result.setdefault(item, specific_defs[item])
            elif item in COMMON_CONTEXTS:
                result.setdefault(item, COMMON_CONTEXTS[item])
            else:
                # Still not found! bad definition
                raise AttributeError("Cannot find definition for context {}".format(item))
        else:
            raise TypeError("Only accept str/list, but found {}".format(type(item)))
    return result


def _extract_func(name, members):
    """
    Extract function whose name is `name` from list of members objects

    Args:
        name (str): func name to extract
        members (list): list of member object

    Returns: function object

    """
    for member in members:
        if member[0] == name:
            return member[1]
    return None


def extract_arguments(func, call, members=None):
    """
    Extract children calls and arguments attributes from a function object
    Args:
        func(function object): function object to extract
        call(str): name of child function being called inside func
        members(list): extractor function with the found ast.Call,
                    default to get first string argument

    Returns:
        calls (set): set of extracted values
        attrs (set): set of attributes

    """
    module = inspect.getmodule(func)
    if not members:
        members = inspect.getmembers(module, inspect.isfunction)
    # Get source from function
    source = inspect.getsource(func)
    # Get ast tree for this source code
    root_node = ast.parse(source)
    if not isinstance(root_node, ast.Module) or not isinstance(root_node.body[0], ast.FunctionDef):
        raise AttributeError("Expect function definition")

    root_func = root_node.body[0]
    # Get root args, only support first arg
    # TODO: support multiple args fetching
    root_arg = root_func.args.args[0].arg if len(root_func.args.args) > 0 else None
    calls = set()
    attrs = set()
    # Walk through all descendants recursively
    for node in ast.walk(root_node):
        # Check for Call and Attribute
        # Attribute first
        if isinstance(node, ast.Attribute):
            if hasattr(node.value, 'id') and node.value.id == root_arg:
                attrs.add(node.attr)
            continue
        # Early termination if not Call node with Name function
        elif not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue

        if node.func.id == call:
            calls.add(node.args[0].s)
        else:
            # Check recursively from member if member is in the same module
            member = _extract_func(node.func.id, members)
            if member:
                _calls, _attrs = extract_arguments(member, call, members)
                calls.update(_calls)
                attrs.update(_attrs)
    return calls, attrs
