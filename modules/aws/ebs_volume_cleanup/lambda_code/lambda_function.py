"""
Lambda function to clean up old EBS volumes.
It assumes roles in target accounts, deletes EBS volumes that are past their deletion date, 
and logs any errors.
It also sends notifications via SNS if any issues occur during the process.
"""
import os
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
import botocore

AWS_REGION = os.environ['AWS_REGION']
CROSS_ACCOUNT_ROLE = os.environ['CROSS_ACCOUNT_ROLE']
EBS_VOLUME_DDB_TABLE = os.environ['EBS_VOLUME_TABLE']
CLEANUP_SAVINGS_TABLE = os.environ['CLEANUP_SAVINGS_TABLE']
SNSTOPICARN = os.environ['SNS_ARN']

error_log = []

def assume_new_account_role(account_id):
    """
    Assume a role in a different AWS account.
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
    Get a boto3 EC2 client for a specific AWS account and region.
    Args:
        access_key (str): Access key for the AWS account.
        secret_access_key (str): Secret access key for the AWS account.
        session_token (str): Session token for the AWS account.
        region (str): AWS region for the EC2 client.
    Returns:
        boto3.client: Boto3 EC2 client for the specified account and region.
    """
    ec2_client = boto3.client('ec2', aws_access_key_id=access_key, \
        aws_secret_access_key=secret_access_key, \
        aws_session_token=session_token, region_name=region)

    return ec2_client

def remove_ebs_volume_ddb_record(volume_id):
    """
    Remove EBS Volume record from DynamoDB table.
    Args:
        volume_id (str): The ID of the EBS volume to remove.
    """
    try:
        primary_session = boto3.Session()
        dynamodb_client = primary_session.client('dynamodb')

        dynamodb_client.delete_item(
            TableName=EBS_VOLUME_DDB_TABLE,
            Key={
                'VolumeId': {
                    'S': volume_id
                }
            }
        )

    except ClientError as e:
        error_message = f"Error in {EBS_VOLUME_DDB_TABLE} DynamoDB item removal: {str(e)}"
        print(error_message)
        error_log.append(error_message)

    return

def delete_ebs_volume(volume_id, account_id, region):
    """
    Deletes an EBS volume.
    Args:
        volume_id (str): The ID of the EBS volume to delete.
        account_id (str): The ID of the AWS account.
        region (str): The AWS region where the volume is located.
    """
    access_key, secret_access_key, session_token = assume_new_account_role(account_id)
    ec2_client = get_multi_account_ec2_client(access_key, secret_access_key, session_token, region)

    try:
        ec2_client.delete_volume(
          VolumeId=volume_id,
          DryRun=False
        )

    except ClientError as e:
        error_message = f"Error in deleting EBS Volume ({volume_id}): {str(e)}"
        print(error_message)
        error_log.append(error_message)

    return

def delete_old_ebs_volumes():
    """
    Deletes EBS volumes older than 30 days.
    """
    try:
        primary_session = boto3.Session()
        dynamodb_client = primary_session.client('dynamodb')

        today_date = datetime.now().strftime('%Y-%m-%d')

        scan_response = dynamodb_client.scan(TableName=EBS_VOLUME_DDB_TABLE)

        for table_item in scan_response['Items']:
            if today_date > table_item['DeletionDate']['S'] and table_item['ExceptionFlag']['S'] == 'False':
                print('Remove: ', table_item['VolumeId']['S'], "in", table_item['AccountName']['S'], "with deletion date:", table_item['DeletionDate']['S'] )
                create_cost_saving_ddb_record(table_item)
                delete_ebs_volume(table_item['VolumeId']['S'], table_item['AccountId']['S'], table_item['ResourceRegion']['S'])
                remove_ebs_volume_ddb_record(table_item['VolumeId']['S'])

    except ClientError as e:
        error_message = f"Error deleting EBS volume and removing it from DDB table: {str(e)}"
        print(error_message)
        error_log.append(error_message)

def create_cost_saving_ddb_record(deleted_volume):
    """
    Creates a cost-saving record in the DynamoDB table for the deleted EBS volume.
    Args:
        deleted_volume (dict): The deleted EBS volume record.
    """
    today_date = datetime.now().strftime('%Y-%m-%d')

    try:
        primary_session = boto3.Session()
        dynamodb_client = primary_session.client('dynamodb')

        # Add to table
        dynamodb_client.update_item(
            Key={
                'ResourceId': {
                    'S': deleted_volume['VolumeId']['S'],
                }
            },
            UpdateExpression="SET ResourceType= :resourceType, \
                AccountId = :accountId, \
                DeletionDate = :date, \
                ExceptionFlag = :exception, \
                AccountName = :accountName, \
                ResourceRegion = :region, \
                ResourceState = :state, \
                VolumeType = :volumeType, \
                VolumeSize = :volumeSize, \
                VolumeIops = :volumeIops, \
                VolumeThroughput = :volumeThroughput, \
                MonthlyCost = :monthlyCost",
            ConditionExpression="attribute_not_exists(VolumeId)",
            ExpressionAttributeValues={
                ':resourceType': {'S': 'EBS Volume'},
                ':accountId': {'S': deleted_volume['AccountId']['S']},
                ':date': {'S': today_date},
                ':exception': {'S': deleted_volume['ExceptionFlag']['S']},
                ':accountName': {'S': deleted_volume['AccountName']['S']},
                ':region': {'S': deleted_volume['ResourceRegion']['S']},
                ':state': {'S': deleted_volume['ResourceState']['S']},
                ':volumeType': {'S': deleted_volume['VolumeType']['S']},
                ':volumeSize': {'N': str(deleted_volume['VolumeSize']['N'])},
                ':volumeIops': {'N': str(deleted_volume['VolumeIops']['N'])},
                ':volumeThroughput': {'N': str(deleted_volume['VolumeThroughput']['N'])},
                ':monthlyCost': {'N': str(deleted_volume['MonthlyCost']['N'])}
            },
            TableName=CLEANUP_SAVINGS_TABLE,
        )

    except ClientError as e:
        error_message = f"Error in DynamoDB update_item ({deleted_volume['VolumeId']}): {str(e)}"
        print('ResourceId:', deleted_volume['VolumeId']['S'], ', AccountId:', \
            deleted_volume['AccountId']['S'], ', DeletionDate:', \
            deleted_volume['DeletionDate']['S'], ', ExceptionFlag:', \
            deleted_volume['ExceptionFlag']['S'], ', AccountName:',  \
            deleted_volume['AccountName']['S'], ', ResourceRegion:', \
            deleted_volume['ResourceRegion']['S'], ', ResourceState:',  \
            deleted_volume['ResourceState']['S'], ', VolumeType:', \
            deleted_volume['VolumeType']['S'], ', VolumeSize:', \
            str(deleted_volume['VolumeSize']['N']), ', VolumeIops:', \
            str(deleted_volume['VolumeIops']['N']), ', MonthlyCost:', \
            str(deleted_volume['MonthlyCost']['N']))
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
            TopicArn=SNSTOPICARN,
            Message=sns_input,
            Subject=subject_message,
        )
        print(response)
    except botocore.exceptions.ClientError:
        print("Couldn't publish message to topic %s.", SNSTOPICARN)
        raise
    except Exception as e:
        print("Encountered Unknown Error when publishing to SNS Topic", SNSTOPICARN, " in Validation Lambda: ", e)
        raise
    return

def lambda_handler(event, context):
    """
    Lambda function to clean up old EBS volumes.
    Args:
        event (_type_): _description_
        context (_type_): _description_
    Returns:
        _type_: _description_
    """
    print("Event: ", event, "Context: ", context)
    delete_old_ebs_volumes()

    if error_log:
        message = ""
        for error in error_log:
            message += error + ",\n"
        print(message)
        publish_sns_topic('EBS Volume Cleanup Issues', message)

    return {
        'statusCode': 200,
        'body': 'EBS Cleanup Completed Successfully'
    }
