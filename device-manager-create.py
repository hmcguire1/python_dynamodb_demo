#!/usr/bin/env python3
import boto3


table_name = 'device-manager'
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')


table = dynamodb.meta.client.create_table(
    AttributeDefinitions=[
        {
            'AttributeName': 'PK',
            'AttributeType': 'S'
        },
        {
            'AttributeName': 'SK',
            'AttributeType': 'S'
        }
    ],
    TableName=table_name,
    KeySchema=[
        {
            'AttributeName': 'PK',
            'KeyType': 'HASH'
        },
        {
            'AttributeName': 'SK',
            'KeyType': 'RANGE'
        },
    ],
    BillingMode='PAY_PER_REQUEST'
)


#wait for table to be created
dynamodb.meta.client.get_waiter('table_exists').wait(TableName=table_name)


