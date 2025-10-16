"""
Handles the Lambda function events for EBS Snapshot Cleanup.
Returns:
    dict: The response object.
"""
import os
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
import botocore

AWS_REGION = os.environ['AWS_REGION']
CROSS_ACCOUNT_ROLE = os.environ['CROSS_ACCOUNT_ROLE']
CLEANUP_SAVINGS_TABLE = os.environ['CLEANUP_SAVINGS_TABLE']
DELETION_TABLE = os.environ['SNAPSHOT_DELETION_TABLE']
SNS_TOPIC_ARN=os.environ['SNS_ARN']
DYNAMODB_TABLE_REGION = os.environ['DYNAMODB_TABLE_REGION']

config = Config(
  retries = {
      'max_attempts': 2,
      'mode': 'standard'
  }
)

today_date = datetime.now().strftime('%Y-%m-%d')
error_log = []

def assume_new_account_role(account_id):
    """
    Assumes a role in a different AWS account.
    Args:
        account_id (str): The ID of the account to assume the role in.
    Returns:
        tuple: A tuple containing the access key, secret access key, and session token.
    """
    sts_connection = boto3.client('sts')
    acct_connection = sts_connection.assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/{CROSS_ACCOUNT_ROLE}",
        RoleSessionName="cross_acct_lambda"
    )

    access_key = acct_connection['Credentials']['AccessKeyId']
    secret_access_key = acct_connection['Credentials']['SecretAccessKey']
    session_token = acct_connection['Credentials']['SessionToken']

    return access_key, secret_access_key, session_token

def get_multi_account_ec2_client(access_key, secret_access_key, session_token, region):
    """
    Creates an EC2 client for a specific AWS region using temporary credentials.
    Args:
        access_key (str): The access key for the assumed role session.
        secret_access_key (str): The secret access key for the assumed role session.
        session_token (str): The session token for the assumed role session.
        region (str): The AWS region to create the EC2 client for.
    Returns:
        boto3.client: A boto3 EC2 client configured with the specified credentials and region.
    """
    ec2_client = boto3.client('ec2', aws_access_key_id=access_key, aws_secret_access_key=secret_access_key, aws_session_token=session_token, region_name=region)

    return ec2_client

def scan_snapshot_ddb_records(table_name):
    """
    Scan the DynamoDB table for EBS snapshot records.
    Args:
        table_name (str): The name of the DynamoDB table to scan.
    Returns:
        list: A list of EBS snapshot records from the DynamoDB table.
    """
    scan_response = {}

    try:
        primary_session = boto3.Session()
        dynamodb_client = primary_session.client('dynamodb', region_name=DYNAMODB_TABLE_REGION)
        scan_response = dynamodb_client.scan(TableName=table_name)
    except ClientError as e:
        error_message = f"Error in DynamoDB scan: {str(e)}"
        print(error_message)

    return scan_response['Items']

def remove_snapshot_ddb_record(snapshot_id):
    """
    Removes an EBS Snapshot record from the DynamoDB table.
    Args:
        snapshot_id (str): The ID of the snapshot to remove.
    """
    try:
        primary_session = boto3.Session()
        dynamodb_client = primary_session.client('dynamodb', region_name=DYNAMODB_TABLE_REGION)

        dynamodb_client.delete_item(
            TableName=DELETION_TABLE,
            Key={
                'ResourceId': {
                    'S': snapshot_id
                }
            }
        )

    except ClientError as e:
        error_message = f"Error in {DELETION_TABLE} DynamoDB scan and processing: {str(e)}"
        print(error_message)
        error_log.append(error_message)

    return

def delete_old_snapshots():
    """
    Deletes EBS snapshots that are older than 90 days.
    """
    seven_days_ago = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    old_snapshots = scan_snapshot_ddb_records(DELETION_TABLE)
    count = 0
    for snapshot in old_snapshots:
        print(snapshot)
        if snapshot['ExceptionFlag']['S'] == 'False' and today_date > snapshot['DeletionDate']['S']:
            if snapshot['ConnectedResource']['S'] == "" or snapshot['LastUpdated']['S'] < seven_days_ago:
                count += 1
                try:
                    access_key, secret_access_key, session_token = assume_new_account_role(snapshot['AccountId']['S'])
                    ec2_client = get_multi_account_ec2_client(access_key, secret_access_key, session_token, snapshot['ResourceRegion']['S'])
                    ec2_client.delete_snapshot(SnapshotId=snapshot['ResourceId']['S'], DryRun=False)
                    print("Creating snapshot savings record:", snapshot)
                    create_cost_saving_ddb_record(snapshot)
                    remove_snapshot_ddb_record(snapshot['ResourceId']['S'])
                except ClientError as e:
                    error_message = f'Error deleting snapshot {snapshot["ResourceId"]["S"]} in account {snapshot["AccountName"]["S"]} in region {snapshot["ResourceRegion"]["S"]}: {e}'
                    client_error_message = str(e)
                    if "(InvalidSnapshot.InUse)" in client_error_message:
                        resource_substring = client_error_message[144:165] if len(client_error_message) > 166 else client_error_message[144:] 
                        if resource_substring.startswith("ami-"):
                            update_snapshot_ddb_record(snapshot['ResourceId']['S'], resource_substring)
                        else:
                            error_log.append(error_message)
                    continue
    print(count)

def create_cost_saving_ddb_record(snapshot_item):
    """
    Creates a cost-saving record for an EBS Snapshot in the DynamoDB table.
    Args:
        snapshot_item (dict): The EBS Snapshot record to save.
    """
    try:
        primary_session = boto3.Session()
        dynamodb_client = primary_session.client('dynamodb', region_name=DYNAMODB_TABLE_REGION)

        # Add to table
        dynamodb_client.update_item(
            Key={
                'ResourceId': {
                    'S': snapshot_item['ResourceId']['S'],
                }
            },
            UpdateExpression="SET ResourceType= :resourceType, AccountId = :accountId, \
              DeletionDate = :date, ExceptionFlag = :exception, AccountName = :accountName, \
                ResourceRegion = :region, ResourceState = :state, StorageTier = :storageTier, \
                VolumeSize = :volumeSize, MonthlyCost = :monthlyCost",
            ConditionExpression="attribute_not_exists(ResourceId)",
            ExpressionAttributeValues={
                ':resourceType': {'S': 'EBS Snapshot'},
                ':accountId': {'S': snapshot_item['AccountId']['S']},
                ':date': {'S': snapshot_item['DeletionDate']['S']},
                ':exception': {'S': snapshot_item['ExceptionFlag']['S']},
                ':accountName': {'S': snapshot_item['AccountName']['S']},
                ':region': {'S': snapshot_item['ResourceRegion']['S']},
                ':state': {'S': snapshot_item['ResourceState']['S']},
                ':storageTier': {'S': snapshot_item['StorageTier']['S']},
                ':volumeSize': {'N': str(snapshot_item['VolumeSize']['N'])},
                ':monthlyCost': {'N': str(snapshot_item['MonthlyCost']['N'])}
            },
            TableName=CLEANUP_SAVINGS_TABLE,
        )

    except ClientError as e:
        error_message = f"Error in DynamoDB update_item ({snapshot_item['SnapshotId']}): {str(e)}"
        print('ResourceId:', snapshot_item['SnapshotId'], ', AccountId:', snapshot_item['AccountId'], ', AccountName:',  snapshot_item['AccountName'], ', Region:', snapshot_item['Region'], ', VolumeSize:', str(snapshot_item['VolumeSize']), ', MonthlyCost:', str(snapshot_item['MonthlyCost']))
        print(error_message)

def update_snapshot_ddb_record(snapshot_id, connected_resource):
    """
    Updates the DynamoDB record for an EBS Snapshot with the connected resource information.
    Args:
        snapshot_id (str): The ID of the snapshot to update.
        connected_resource (str): The ID of the connected resource.
    """
    print("Updating snapshot: ", snapshot_id, "with connected resource: ", connected_resource)

    try:
        primary_session = boto3.Session()
        dynamodb_client = primary_session.client('dynamodb')

        # Add to table
        dynamodb_client.update_item(
            Key={
                'ResourceId': {
                    'S': snapshot_id,
                }
            },
            UpdateExpression="SET ConnectedResource = :connectedResource, LastUpdated = :lastUpdated",
            ExpressionAttributeValues={
                ':connectedResource': {'S': connected_resource},
                ':lastUpdated': {'S': today_date}
            },
            TableName=DELETION_TABLE,
        )
    except ClientError as e:
        error_message = f"Error in DynamoDB {DELETION_TABLE} update_item ({snapshot_id}): {str(e)}"
        print(error_message)
        error_log.append(error_message)

def publish_sns_topic(subject_message, sns_input):
    """Publish a message to an SNS topic.

    Args:
        subject_message (str): The subject line for the SNS message.
        sns_input (str): The message body for the SNS message.
    """
    try:
        sns_client = boto3.client('sns')
        response = sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=sns_input,
            Subject=subject_message,
        )
        print(response)
    except botocore.exceptions.ClientError:
        print("Couldn't publish message to topic %s.", SNS_TOPIC_ARN)
        raise
    except Exception as e:
        print("Encountered Unknown Error when publishing to SNS Topic", SNS_TOPIC_ARN, " in Validation Lambda: ", e)
        raise

def lambda_handler(event, context):
    """Handles the Lambda function events.

    Args:
        event (dict): The event data passed to the Lambda function.
        context (LambdaContext): The context object containing runtime information.

    Returns:
        dict: The response object.
    """
    print("Event: ", event, "Context: ", context)
    delete_old_snapshots()

    if error_log:
        message = ""
        for error in error_log:
            message += error + ",\n"
        print(message)
        publish_sns_topic('EBS Snapshot Cleanup Issues', message)

    return {
          'statusCode': 200,
          'body': 'EBS Snapshot Cleanup Completed Successfully'
    }
