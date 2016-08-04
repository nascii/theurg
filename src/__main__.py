import argparse

import config

def parse_args():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    agg = subparsers.add_parser('aggregate')
    agg.add_argument('leagues', metavar='league', nargs='*', type=int,
                     default=config.get('aggregation', 'leagues'))
    agg.add_argument('--db-path', default=config.get_path('aggregation', 'db-path'))
    agg.add_argument('--api-key')
    agg.add_argument('--api-key-path', default=config.get_path('aggregation', 'api-key-path'))
    agg.add_argument('--retry-limit', type=int, default=config.get('aggregation', 'retry-limit'))
    agg.add_argument('--retry-delay', type=int, default=config.get('aggregation', 'retry-delay'))

    args = parser.parse_args()

    # `api-key-path` to `api-key` if needed.
    if not args.api_key:
        with open(args.api_key_path) as api_key_file:
            args.api_key = api_key_file.read().strip()

    return args

def aggregate(args):
    from aggregator import Aggregator

    agg = Aggregator(args.db_path, args.api_key, args.retry_limit, args.retry_delay)
    agg.complement(args.leagues)

def main():
    args = parse_args()

    if args.command == 'aggregate':
        aggregate(args)

main()
