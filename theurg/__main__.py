import argparse

import config

def parse_args():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    p = subparsers.add_parser('aggregate')
    p.add_argument('leagues', metavar='league', nargs='*', type=int,
                     default=config.get('aggregation', 'leagues'))
    p.add_argument('--db-path', default=config.get_path('aggregation', 'db-path'))
    p.add_argument('--api-key')
    p.add_argument('--api-key-path', default=config.get_path('aggregation', 'api-key-path'))
    p.add_argument('--retry-limit', type=int, default=config.get('aggregation', 'retry-limit'))
    p.add_argument('--retry-delay', type=int, default=config.get('aggregation', 'retry-delay'))

    p = subparsers.add_parser('predict')
    p.add_argument('--db-path', default=config.get_path('aggregation', 'db-path'))

    args = parser.parse_args()

    # `api-key-path` to `api-key` if needed.
    if hasattr(args, 'api_key') and not args.api_key:
        with open(args.api_key_path) as api_key_file:
            args.api_key = api_key_file.read().strip()

    return args

def aggregate(args):
    from aggregator import Aggregator

    aggregator = Aggregator(args.db_path, args.api_key, args.retry_limit, args.retry_delay)
    aggregator.complement(args.leagues)

def predict(args):
    from predictor import Predictor

    predictor = Predictor(args.db_path)
    predictor.train()

def main():
    args = parse_args()

    if args.command == 'aggregate':
        aggregate(args)
    elif args.command == 'predict':
        predict(args)

main()
