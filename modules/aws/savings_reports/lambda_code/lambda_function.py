"""
Lambda function to calculate cost savings from resource cleanup.
"""
import os
import csv
import json
import math
from datetime import date
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

EBS_VOLUME_TABLE = os.environ['EBS_VOLUME_TABLE']
EBS_FILE_NAME = 'projected_ebs_cost_savings.csv'

EBS_SNAPSHOT_TABLE = os.environ['EBS_SNAPSHOT_TABLE']
SNAPSHOT_FILE_NAME = 'projected_snapshot_cost_savings.csv'

SAVINGS_DDB_TABLE = 'resource-cleanup-savings'
S3_STORAGE_BUCKET = 'platformeng-enterprise-uswe2-prod-524024217541'
FILE_NAME = 'cost_savings.csv'

def months_diff(start, end):
    """
    Calculate the number of months between two dates.
    Args:
        start (datetime): The start date.
        end (datetime): The end date.
    Returns:
        int: The number of months between the two dates.
    """
    return math.floor((end - start).days / 30)

def total_ebs_volumes():
    """
    Calculate total EBS volume costs from DynamoDB.
    """
    s3_client = boto3.client('s3')
    csv_data = []

    try:
        dynamodb_client = boto3.client('dynamodb', region_name = 'us-west-2')
        ebs_volumes_response = dynamodb_client.scan(TableName=EBS_VOLUME_TABLE)
        items = ebs_volumes_response['Items']

        for item in items:
            csv_item = [{'VolumeId': item['VolumeId']['S'], \
                'ResourceState': item['ResourceState']['S'], \
                'AccountId': item['AccountId']['S'], \
                'AccountName': item['AccountName']['S'], \
                'ResourceRegion': item['ResourceRegion']['S'], \
                'ExceptionFlag': item['ExceptionFlag']['S'], \
                'VolumeType': item['VolumeType']['S'], \
                'VolumeIops': item['VolumeIops']['N'], \
                'VolumeSize': item['VolumeSize']['N'], \
                'VolumeThroughput': item['VolumeThroughput']['N'], \
                'DeletionDate': item['DeletionDate']['S'], \
                'MonthlyCost': item['MonthlyCost']['N']}]
            csv_data.extend(csv_item)

    except ClientError as e:
        error_message = f"Error in DynamoDB scan: {str(e)}"
        print(error_message)

    with open(f'/tmp/{EBS_FILE_NAME}', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['VolumeId','ResourceType', 'ResourceState',\
            'AccountId', 'AccountName', 'ResourceRegion', 'ExceptionFlag', \
            'VolumeType', 'VolumeIops', 'VolumeSize', 'VolumeThroughput', \
            'DeletionDate', 'MonthlyCost']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_data)

    s3_client.upload_file(f'/tmp/{EBS_FILE_NAME}', S3_STORAGE_BUCKET, EBS_FILE_NAME)

def total_ebs_snapshots():
    """
    Calculate total EBS snapshot costs from DynamoDB.
    """
    s3_client = boto3.client('s3')
    csv_data = []

    try:
        dynamodb_client = boto3.client('dynamodb', region_name = 'us-west-2')
        ebs_snapshot_response = dynamodb_client.scan(TableName=EBS_SNAPSHOT_TABLE)
        items = ebs_snapshot_response['Items']

        for item in items:
            csv_item = [{'ResourceId': item['ResourceId']['S'], \
                'ResourceType': 'EBS Snapshot', \
                'ResourceState': item['ResourceState']['S'], \
                'AccountId': item['AccountId']['S'], \
                'AccountName': item['AccountName']['S'], \
                'ResourceRegion': item['ResourceRegion']['S'], \
                'ExceptionFlag': item['ExceptionFlag']['S'], \
                'VolumeSize': item['VolumeSize']['N'], \
                'StorageTier': item['StorageTier']['S'], \
                'ConnectedResource': item['ConnectedResource']['S'], \
                'DeletionDate': item['DeletionDate']['S'], \
                'MonthlyCost': item['MonthlyCost']['N']}]
            csv_data.extend(csv_item)

    except ClientError as e:
        error_message = f"Error in DynamoDB scan: {str(e)}"
        print(error_message)

    with open(f'/tmp/{SNAPSHOT_FILE_NAME}', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['ResourceId', 'ResourceType', 'ResourceState', \
            'AccountId', 'AccountName', 'ResourceRegion', 'ExceptionFlag', \
            'VolumeSize', 'StorageTier', 'ConnectedResource', 'DeletionDate', \
            'MonthlyCost']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_data)

    s3_client.upload_file(f'/tmp/{SNAPSHOT_FILE_NAME}', S3_STORAGE_BUCKET, SNAPSHOT_FILE_NAME)

def total_resource_savings():
    """
    Calculate total resource savings from DynamoDB.
    """
    s3_client = boto3.client('s3')
    csv_data = []

    try:
        dynamodb_client = boto3.client('dynamodb', region_name = 'us-west-2')
        response = dynamodb_client.scan(TableName=SAVINGS_DDB_TABLE)
        total_cost_savings = 0

        for item in response['Items']:
            total_cost_savings += float(item['MonthlyCost']['N'])
            storage_tier = ""
            volume_iops = 0
            volume_throughput = 0
            volume_type = ""
            months = months_diff(datetime.strptime(item['DeletionDate']['S'], \
                "%Y-%m-%d").date(), date.today())

            if item.get('StorageTier', '') != '':
                storage_tier = item['StorageTier']['S']
            if item.get('VolumeIops', '') != '':
                volume_iops = item['VolumeIops']['N']
            if item.get('VolumeThroughput', '') != '':
                volume_throughput = item['VolumeThroughput']['N']
            if item.get('VolumeType', '') != '':
                volume_type = item['VolumeType']['S']

            csv_item = [{'ResourceId': item['ResourceId']['S'], \
                'ResourceType': item['ResourceType']['S'], \
                'ResourceState': item['ResourceState']['S'], \
                'AccountId': item['AccountId']['S'], \
                'AccountName': item['AccountName']['S'], \
                'ResourceRegion': item['ResourceRegion']['S'], \
                'ExceptionFlag': item['ExceptionFlag']['S'], \
                'VolumeType': volume_type, \
                'VolumeIops': volume_iops, \
                'VolumeSize': item['VolumeSize']['N'], \
                'VolumeThroughput': volume_throughput, \
                'StorageTier': storage_tier, \
                'DeletionDate': item['DeletionDate']['S'], \
                'MonthsSinceDeletion': months, \
                'MonthlyCost': item['MonthlyCost']['N']}]
            csv_data.extend(csv_item)

    except ClientError as e:
        error_message = f"Error in DynamoDB scan: {str(e)}"
        print(error_message)

    final_line_totals = [{'ResourceId': "" ,'ResourceType': "", \
        'ResourceState': "", 'AccountId': "", 'AccountName': "", \
        'ResourceRegion': "", 'ExceptionFlag': "", 'VolumeType': "", \
        'VolumeIops': "", 'VolumeSize': "", 'VolumeThroughput': "", \
        'StorageTier': "", 'DeletionDate': "", 'MonthsSinceDeletion': '', \
        'MonthlyCost': f'{total_cost_savings:.2f}'}]
    csv_data.extend(final_line_totals)

    with open(f'/tmp/{FILE_NAME}', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['ResourceId','ResourceType', 'ResourceState','AccountId', \
            'AccountName', 'ResourceRegion', 'ExceptionFlag', 'VolumeType', \
            'VolumeIops', 'VolumeSize', 'VolumeThroughput', 'StorageTier', \
            'DeletionDate', 'MonthsSinceDeletion', 'MonthlyCost']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_data)

    s3_client.upload_file(f'/tmp/{FILE_NAME}', S3_STORAGE_BUCKET, FILE_NAME)

def lambda_handler(event, context):
    """
    Main Lambda function handler.
    Args:
        event (dict): The event data.
        context (object): The context object.
    Returns:
        dict: The response object.
    """
    print("Event: ", event, "Context: ", context)

    total_resource_savings()
    total_ebs_volumes()
    total_ebs_snapshots()

    return {
        'statusCode': 200,
        'body': json.dumps('Cost Savings Files complete')
    }
