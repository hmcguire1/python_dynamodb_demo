import decimal
import json
from functools import reduce


from flask import Flask, request, Response, jsonify
import flask.json

import boto3
#from botocore.exceptions import ClientError, PaginationError
from boto3.dynamodb.conditions import Key, Attr, And #AWESOME
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer #AWESOME

from put_expr import put_expression

#Custom JSON Encoder to handle boto3 Decmial type.
class JSONEncoder(flask.json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            # Convert decimal instances to float.
            return float(obj)
        return super(JSONEncoder, self).default(obj)


app = Flask(__name__)
app.json_encoder = JSONEncoder

table_name = 'device-manager'
dynamodb = boto3.resource('dynamodb', region_name='us-east-1') #endpoint_url="https://localhost:5000"
table = dynamodb.Table(table_name)
query_paginator = dynamodb.meta.client.get_paginator('query')

serializer = TypeSerializer()
deserializer = TypeDeserializer()

ASSET_ATTRIBUTES = (
    'AssetName',
    'AssetType',
    'CostCenter',
    'CostPerHour',
    'CostType',
    'Department',
    'Model',
    'OperatingSystem',
    'Vendor'
)

USER_ATTRIBUTES = (
    'Active',
    'Admin',
    'Department',
    'FirstName',
    'LastName',
    'Title',
    'Username'
)

def api_list(request_object):
    '''
    Function to List and filter all items passed on entity type.
    Takes in request_object any query params passed that are not for domain.
    '''

    domain = f"domain::{request_object.args.get('domain')}"
    entity_type = f"{request_object.base_url.split('/')[-1]}::"

    # gather all query paramaters that are not 'domain'
    kwargs = [(k, v) for k,v in request_object.args.items() if k != 'domain']

    if entity_type == 'asset::':
        projection_expression = ','.join([item for item in ASSET_ATTRIBUTES])
    elif entity_type == 'user::':
        projection_expression = ','.join([item for item in USER_ATTRIBUTES])

    if not kwargs:
        response = query_paginator.paginate(
            TableName=table_name,
            KeyConditionExpression=
                Key('PK').eq(domain) &
                Key('SK').begins_with(entity_type),
            ProjectionExpression=projection_expression
        )

        items = [item for item in response][0].get('Items')

        return items

    else:
        response = query_paginator.paginate(
            TableName=table_name,
            KeyConditionExpression=
                Key('PK').eq(domain) &
                Key('SK').begins_with(entity_type),
            FilterExpression=reduce(And, ([Attr(k).eq(v) for k,v in kwargs])),
            ProjectionExpression=projection_expression
        )

        items = [item for item in response][0].get('Items')

        return items


def api_item(request_object):
    '''
    Function to work directly with an item.
    Takes in a request_object.
    '''

    domain = f"domain::{request_object.args.get('domain')}"
    entity_type = f"{request_object.base_url.split('/')[-2]}::"
    item = f"{request_object.base_url.split('/')[-1]}"

    if entity_type == 'asset::':
        projection_expression = ','.join([item for item in ASSET_ATTRIBUTES])

        if request_object.method in ('PUT', 'POST'):
            keys = [key for key in request_object.get_json().keys()]
            param_constraint = all([(item in keys) for item in ASSET_ATTRIBUTES])

    elif entity_type == 'user::':
        projection_expression = ','.join([item for item in USER_ATTRIBUTES])

        if request_object.method in ('PUT', 'POST'):
            keys = [key for key in request_object.get_json().keys()]
            param_constraint = all([(item in keys) for item in USER_ATTRIBUTES])

    table_item = table.get_item(
        Key=dict(
            PK=domain,
            SK=entity_type + item
        ),
        ProjectionExpression=projection_expression
    ).get('Item', None)

    if request_object.method == 'GET' and table_item:
        return jsonify(table_item)

    if request_object.method == 'DELETE' and table_item:
        response = table.delete_item(
            Key=dict(
                PK=domain,
                SK=entity_type + item
            )
        )

        if response:
            return Response(status=204)
        else:
            return Response(status=400)

    if request_object.method in ('POST', 'PUT'):
        request_json_data = request.get_json()
        keys = [key for key in request_json_data.keys() if key != 'domain']
        put_json_data = request_json_data.copy()

        put_json_data.update(
            dict(
                PK=domain,
                SK=entity_type + item,
                EntityType=entity_type[:-2]
            )
        )

    if request_object.method == 'POST':
        if param_constraint:
            table.put_item(Item=put_json_data)

            return Response(status=201)
        else:
            return Response(status=400)

    if request_object.method == 'PUT' and table_item:
        expression_tuple = put_expression(request_json_data)

        table.update_item(
            Key=dict(
                PK=domain,
                SK=entity_type + item
            ),
            ExpressionAttributeNames=expression_tuple.expression_names, # {'#val1': 'val1', '#val2': 'val2'}
            ExpressionAttributeValues=expression_tuple.expression_values, # {':val1': 1, ':val2': 2}
            UpdateExpression=expression_tuple.expression, # 'SET #val1 = :val1, #val2 = :val2'
            ReturnValues='ALL_NEW' # New Item after Updated
        )

        return Response(status=204)
    return Response(status=404)


#ASSET ROUTES

# Route that calls api_list function to list and filter all asset entity types.
@app.route('/api/v1/asset', methods=['GET'])
def api_assets():
    if not request.args.get('domain'):
        return Response(status=400)

    items = api_list(request)

    if items:
        return jsonify(items)
    else:
        return Response(status=404)


#Work directly with assets for CRUD operation to single item.
@app.route('/api/v1/asset/<string:asset_name>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_get_asset(asset_name):
    if not request.args.get('domain'):
        return Response(status=400)

    item_response = api_item(request)

    return item_response


#USER ROUTES

# Route that calls api_list function to list and filter all user entity types.
@app.route('/api/v1/user', methods=['GET'])
def api_users():
    if not request.args.get('domain'):
        return Response(status=400)

    items = api_list(request)
    print(items)
    if items:
        return jsonify(items)
    else:
        return Response(status=404)

#Work directly with users for CRUD operation to single item.
@app.route('/api/v1/user/<username>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_get_user(username):
    if not request.args.get('domain'):
        return Response(status=400)

    item_response = api_item(request)

    return item_response














'''
domains = table.query(
    IndexName='EntityType-SK-index',
    KeyConditionExpression=Key('EntityType').eq('domain'),
    ProjectionExpression='DomainName'
).get('Items')

[domain['DomainName'] for domain in domains]
'''
