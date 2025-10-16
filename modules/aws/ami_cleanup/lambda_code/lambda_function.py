"""
Lambda function to clean up AMIs that are older than the deletion date recorded in DynamoDB table

Returns:
    _type_: _description_
"""
import os
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
import botocore

AWS_REGION = os.environ['AWS_REGION']
CROSS_ACCOUNT_ROLE = os.environ['CROSS_ACCOUNT_ROLE']

ACCOUNT_DDB_TABLE = os.environ['ACCOUNT_TABLE']
ACCOUNT_DDB_TABLE_INDEX = 'AccountName-index'

RESOURCE_TABLE = os.environ['AMI_TABLE']
CLEANUP_SAVINGS_TABLE = os.environ['CLEANUP_SAVINGS_TABLE']

SNSTOPICARN=os.environ['SNS_ARN']

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
    Get an EC2 client for a specific AWS account and region.
    Args:
        access_key (str): Access key for the AWS account.
        secret_access_key (str): Secret access key for the AWS account.
        session_token (str): Session token for the AWS account.
        region (str): AWS region to connect to.
    Returns:
        boto3.client: EC2 client for the specified AWS account and region.
    """
    ec2_client = boto3.client('ec2', aws_access_key_id=access_key, \
      aws_secret_access_key=secret_access_key, aws_session_token=session_token, region_name=region)

    return ec2_client

def remove_resource_ddb_record(resource_id):
    """Remove a resource record from the DynamoDB table.

    Args:
        resource_id (str): The ID of the resource to remove.
    """
    try:
        primary_session = boto3.Session()
        dynamodb_client = primary_session.client('dynamodb', region_name='us-west-2')

        dynamodb_client.delete_item(
            TableName=RESOURCE_TABLE,
            Key={
                'ResourceId': {
                    'S': resource_id
                }
            }
        )

    except ClientError as e:
        error_message = f"Error in {RESOURCE_TABLE} DynamoDB item removal: {str(e)}"
        print(error_message)
        error_log.append(error_message)

    return

def delete_resource(resource_id, account_id, region):
    """
    Delete a resource from a specific AWS account and region.
    Args:
        resource_id (str): The ID of the resource to delete.
        account_id (str): The ID of the account where the resource resides.
        region (str): The AWS region where the resource resides.
    """
    access_key, secret_access_key, session_token = assume_new_account_role(account_id)
    ec2_client = get_multi_account_ec2_client(access_key, secret_access_key, session_token, region)

    try:
        ec2_client.deregister_image(
          ResourceId=resource_id,
          DryRun=True
        )

    except ClientError as e:
        error_message = f"Error in deregistering AMI ({resource_id}): {str(e)}"
        print(error_message)
        error_log.append(error_message)

    return

def delete_old_resources():
    """
    Delete old resources.
    """
    try:
        primary_session = boto3.Session()
        dynamodb_client = primary_session.client('dynamodb', region_name='us-west-2')

        today_date = datetime.now().strftime('%Y-%m-%d')

        scan_response = dynamodb_client.scan(TableName=RESOURCE_TABLE)

        for table_item in scan_response['Items']:
            if today_date > table_item['DeletionDate']['S'] and table_item['ExceptionFlag']['S'] == 'False':
                print('Remove: ', table_item['ResourceId']['S'], "in", table_item['AccountName']['S'], "with deletion date:", table_item['DeletionDate']['S'] )
                delete_resource(table_item['ResourceId']['S'], table_item['AccountId']['S'], table_item['ResourceRegion']['S'])
                remove_resource_ddb_record(table_item['ResourceId']['S'])

    except ClientError as e:
        error_message = f"Error deleting resource and removing it from DDB table: {str(e)}"
        print(error_message)
        error_log.append(error_message)

##### ERROR NOTIFICATION FUNCTIONS #####
# SNS serves as an easy mechanism to alert responsible owners about function errors
def publish_sns_topic(subject_message, sns_input):
    """
    Publish a message to an SNS topic.
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
        print("Encountered Unknown Error when publishing to SNS Topic", SNSTOPICARN, " in Lambda: ", e)
        raise
    return


##### MAIN FUNCTION #####
def lambda_handler(event, context):
    """
    Lambda function to clean up old AMIs.
    Args:
        event (dict): The event data passed to the Lambda function.
        context (LambdaContext): The context object containing runtime information.
    Returns:
        dict: The response object containing the status code and message.
    """
    print("Event: ", event, "Context: ", context)
    delete_old_resources()

    if error_log:
        message = ""
        for error in error_log:
            message += error + ",\n"
        print(message)
        publish_sns_topic('AMI Cleanup Issues', message)

    return {
        'statusCode': 200,
        'body': 'AMI Cleanup Completed Successfully'
    }
