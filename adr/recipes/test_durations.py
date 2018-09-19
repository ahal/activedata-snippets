"""
See the number of tests that have a duration in pre-selected buckets.

.. code-block:: bash

    adr test_durations
"""
from __future__ import print_function, absolute_import

from ..cli import RecipeParser
from ..query import run_query


def run(args):
    parser = RecipeParser('branch', 'build', 'date', 'platform')
    args = parser.parse_args(args)

    result = []
    query_args = vars(args)

    data = next(run_query('test_durations', **query_args))['data']['result.test']

    duration = [1, 2, 5, 10, 20, 30, 45, 60, 90, 120, 150, 'max']
    for index in range(0, len(duration)):
        result.append([duration[index], data[index]])
    result.insert(0, ['Max Duration (seconds)', 'number of tests'])
    return result
