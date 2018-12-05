"""
Get the average and total runtime for build platforms and types.

.. code-block:: bash

    adr config_durations [--branch <branch>]
"""
from __future__ import print_function, absolute_import

from ..recipe import execute_query

# NO need to define query list, use automatic detection
# def get_queries():
#     return ['config_durations']

# NO need to define query list, use automatic detection
# def get_queries():
#     return ['config_durations']

# NO need to define run argument definition, use automatic detection
# def get_run_contexts():
#     return ["sort_key", "limit"]


def run(args):
    # process config data
    data = execute_query('config_durations')
    result = []
    for record in data:
        if isinstance(record[1], list):
            record[1] = record[1][-1]
        if record[2] is None:
            continue
        if record[3] is None:
            continue
        record[3] = round(record[3] / 60, 2)
        record.append(int(round(record[2] * record[3], 0)))
        result.append(record)

    result = sorted(result, key=lambda k: k[args.sort_key], reverse=True)[:args.limit]
    result.insert(0, ['Platform', 'Type', 'Num Jobs', 'Average Hours', 'Total Hours'])
    return result
