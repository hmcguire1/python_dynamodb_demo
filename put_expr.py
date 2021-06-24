from collections import namedtuple

def put_expression(attributes: dict)-> any:
    expression_names = {f"#{k}":k for k,v in attributes.items()}
    expression_values = {f":{k}":v for k,v in attributes.items()}
    expression = "SET " + ', '.join([f"#{k} = :{k}" for k,v in attributes.items()])
    Expression = namedtuple(
        'Expression',
        [
            'expression',
            'expression_names',
            'expression_values'
        ]
    )

    return Expression(expression, expression_names, expression_values)