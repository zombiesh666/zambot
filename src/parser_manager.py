from src.parsers.crossover_parser import CrossoverParser

PARSERS = {
    "crossover": CrossoverParser(),
    # Add other rinks here as we get their feeds
}

def get_parser(parser_type):
    return PARSERS.get(parser_type)
