"""
Lambda function to inventory all self-owned AMIs across all accounts and regions in the Organization
"""
import os
import json
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError
import botocore

AWS_REGION = os.environ['AWS_REGION']
CROSS_ACCOUNT_ROLE = os.environ['CROSS_ACCOUNT_ROLE']

REGIONS = os.environ['ACTIVE_REGIONS'].split(',')
ACCOUNT_DDB_TABLE = os.environ['ACCOUNT_TABLE']
ACCOUNT_DDB_TABLE_INDEX = 'AccountName-index'
AMI_DDB_TABLE = os.environ['AMI_TABLE']
SNSTOPICARN=os.environ['SNS_ARN']

error_log = []

def get_active_accounts():
    """
    Get active accounts from DynamoDB.
    Returns:
        list: A list of active account information.
    """
    try:
        dynamodb_client = boto3.client('dynamodb', region_name = AWS_REGION)
        scan_response = dynamodb_client.scan(TableName=ACCOUNT_DDB_TABLE)
        return scan_response['Items']

    except ClientError as e:
        error_message = f"Error in {ACCOUNT_DDB_TABLE} DynamoDB scan and processing: {str(e)}"
        print(error_message)
        error_log.append(error_message)

    return

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
    Get a boto3 EC2 client for a specific AWS account and region.

    Args:
        access_key (str): The access key for the AWS account.
        secret_access_key (str): The secret access key for the AWS account.
        session_token (str): The session token for the AWS account.
        region (str): The AWS region for the EC2 client.

    Returns:
        boto3.client: A boto3 EC2 client for the specified account and region.
    """
    ec2_client = boto3.client('ec2', aws_access_key_id=access_key, aws_secret_access_key=secret_access_key, aws_session_token=session_token, region_name=region)

    return ec2_client

def get_amis(account_id, account_name, env, regions, access_key, secret_access_key, session_token):
    """
    Get AMIs for a specific account across multiple regions.
    Args:
        account_id (str): The ID of the AWS account.
        account_name (str): The name of the AWS account.
        env (str): The environment (e.g., "prod", "dev").
        regions (list): The list of regions to query for AMIs.
        access_key (str): The access key for the AWS account.
        secret_access_key (str): The secret access key for the AWS account.
        session_token (str): The session token for the AWS account.
    Returns:
        list: A list of AMIs for the specified account and regions.
    """
    amis = []

    date_diff_30_days = datetime.now() + timedelta(days=30)
    thirty_days_date = (datetime(date_diff_30_days.year, date_diff_30_days.month, date_diff_30_days.day)).strftime('%Y-%m-%d')
    date_diff_90_days = datetime.now() + timedelta(days=90)
    ninety_days_date = (datetime(date_diff_90_days.year, date_diff_90_days.month, date_diff_90_days.day)).strftime('%Y-%m-%d')

    for region in regions:
        ami_list_output = []
        try:
            print(f'Getting AMI for account {account_name} in region {region}')
            ec2_client = get_multi_account_ec2_client(access_key, secret_access_key, session_token, region)

            # Get initial ami list
            response = ec2_client.describe_images(Owners=['self'],MaxResults=20)      # ec2_client.describe_images(Filters=[{'Name': 'status','Values': ['available',]}],MaxResults=20)
            ami_list_output = response['Images']

            # Loop describe_images until all amis are added to the ami_list_output
            while 'NextToken' in response:
                response = ec2_client.describe_images(Owners=['self'], MaxResults=20, NextToken=response['NextToken'])
                ami_list_output.extend(response['Images'])

        except ClientError as e:
            error_message = f"Error for {account_name} in {region}: {str(e)}"
            print(error_message)
            error_log.append(error_message)

        # Create a new list of amis from the list of ami responses with all relevant data
        for ami in ami_list_output:
            deletion_date = ninety_days_date if env == "prod" else thirty_days_date

            block_mapping_dictionary = []
            for device in ami['BlockDeviceMappings']:
                if device.get('Ebs', '') != '':
                    block_mapping_dictionary.append(device)

            amis.append({
              'ResourceId': ami['ImageId'],
              'AccountName': account_name, 
              'AccountId': account_id, 
              'Environment': env, 
              'Region': region, 
              'Name': ami['Name'],
              'DeletionDate': deletion_date,
              'Architecture': ami['Architecture'],
              'Platform': ami['PlatformDetails'],
              'State': ami['State'],
              'BlockMappings': block_mapping_dictionary,
              'CreationDate': ami['CreationDate'][:10],
              'LastLaunchedTime': ami['LastLaunchedTime'][:10] if ami.get('LastLaunchedTime', "") != "" else "",
              'Description': ami.get('Description', ""),
              'SourceInstanceId': ami.get('SourceInstanceId', ""),
              'Exception': 'False', 
              'Tags': ami.get('Tags', [])
            })

    return amis

def get_ami(amis, image_id):
    """Get an AMI from the list of AMIs.

    Args:
        amis (list[dict]): List of AMI objects.
        image_id (str): Image ID of the desired AMI.

    Returns:
        dict: The AMI object if found, else None.
    """
    for ami in amis:
        if ami['ResourceId'] == image_id:
            return ami

    return None

def get_ami_ddb_record(image_id):
    """
    Get an AMI record from DynamoDB.
    Args:
        image_id (str): The ID of the AMI to retrieve.
    Returns:
        dict: The AMI record from DynamoDB, or None if not found.
    """
    try:
        primary_session = boto3.Session()
        dynamodb_client = primary_session.client('dynamodb')

        response = dynamodb_client.get_item(
            Key={
                'ResourceId': {
                    'S': image_id,
                },
            },
            TableName=AMI_DDB_TABLE,
        )

        return response

    except ClientError as e:
        error_message = f"Error in {AMI_DDB_TABLE} DynamoDB scan and processing: {str(e)}"
        print(error_message)
        error_log.append(error_message)

def scan_ami_ddb_records(table_name):
    """
    Scan all AMI records from a DynamoDB table.
    Args:
        table_name (str): The name of the table to scan.
    Returns:
        list(dict): A list of AMI records from the table.
    """

    items = []
    scan_response = {}

    try:
        primary_session = boto3.Session()
        dynamodb_client = primary_session.client('dynamodb')
        scan_response = dynamodb_client.scan(TableName=table_name)
        items = scan_response['Items']

        while 'LastEvaluatedKey' in scan_response:
            scan_response = dynamodb_client.scan(TableName=table_name, ExclusiveStartKey=scan_response['LastEvaluatedKey'])
            items.extend(scan_response['Items'])

    except ClientError as e:
        error_message = f"Error in DynamoDB {table_name} scan: {str(e)}"
        print(error_message)
        error_log.append(error_message)

    return items

def remove_ami_ddb_record(ami_id):
    """Remove an AMI record from the DynamoDB table.

    Args:
        ami_id (str): The ID of the AMI to remove.
    """
    try:
        primary_session = boto3.Session()
        dynamodb_client = primary_session.client('dynamodb')

        dynamodb_client.delete_item(
            TableName=AMI_DDB_TABLE,
            Key={
                'ResourceId': {
                    'S': ami_id
                }
            }
        )

    except ClientError as e:
        error_message = f"Error in {AMI_DDB_TABLE} DynamoDB scan and processing: {str(e)}"
        print(error_message)
        error_log.append(error_message)

    return

def create_ami_ddb_record(ami):
    """
    Creates a new AMI record in the DynamoDB table.
    Args:
        ami (dict): The AMI object to be created.
    """
    try:
        primary_session = boto3.Session()
        dynamodb_client = primary_session.client('dynamodb')

        # Add to table
        dynamodb_client.update_item(
            Key={
                'ResourceId': {
                    'S': ami['ResourceId'],
                }
            },
            UpdateExpression="SET AccountId = :accountId, DeletionDate = :date, \
              ExceptionFlag = :exception, AccountName = :accountName, ResourceRegion = :region, \
              ResourceState = :state, AmiName = :name, Architecture = :architecture, \
              Platform = :platform, BlockMappings = :blockMappings, CreationDate = :creationDate, \
              LastLaunchedTime = :lastLaunchedTime, Description = :description, \
              SourceInstanceId = :sourceInstanceId, Tags = :tags",
            ConditionExpression="attribute_not_exists(ResourceId)",
            ExpressionAttributeValues={
                ':accountId': {'S': ami['AccountId']},
                ':date': {'S': ami['DeletionDate']},
                ':exception': {'S': ami['Exception']},
                ':accountName': {'S': ami['AccountName']},
                ':region': {'S': ami['Region']},
                ':state': {'S': ami['State']},
                ':name': {'S': ami['Name']},
                ':architecture': {'S': ami['Architecture']},
                ':platform': {'S': ami['Platform']},
                ':blockMappings': {'S': json.dumps(ami['BlockMappings'])},
                ':creationDate': {'S': ami['CreationDate']},
                ':lastLaunchedTime': {'S': ami['LastLaunchedTime']},
                ':description': {'S': ami['Description']},
                ':sourceInstanceId': {'S': ami['SourceInstanceId']},
                ':tags': {'S': json.dumps(ami['Tags'])},
            },
            TableName=AMI_DDB_TABLE,
        )

    except ClientError as e:
        error_message = f"Error in DynamoDB Creation - update_item ({ami}): {str(e)}"
        print(error_message)
        error_log.append(error_message)

def update_ami_ddb_record(ami):
    """
    Updates an existing AMI record in the DynamoDB table.
    Args:
        ami (dict): The AMI object containing updated information.
    """
    try:
        primary_session = boto3.Session()
        dynamodb_client = primary_session.client('dynamodb')

        # Add to table
        dynamodb_client.update_item(
            Key={
                'ResourceId': {
                    'S': ami['ResourceId'],
                }
            },
            UpdateExpression="SET AmiName = :name, ResourceState = :state, \
                Description = :description, BlockMappings = :blockMappings, \
                LastLaunchedTime = :lastLaunchedTime, Tags = :tags",
            ExpressionAttributeValues={
                ':name': {'S': ami['Name']},
                ':state': {'S': ami['State']},
                ':description': {'S': ami['Description']},
                ':blockMappings': {'S': json.dumps(ami['BlockMappings'])},
                ':lastLaunchedTime': {'S': ami['LastLaunchedTime']},
                ':tags': {'S': json.dumps(ami['Tags'])},
            },
            TableName=AMI_DDB_TABLE,
        )

    except ClientError as e:
        error_message = f"Error in DynamoDB update_item ({ami['ResourceId']}): {str(e)}"
        print(error_message)
        error_log.append(error_message)

def update_ddb_records(amis):
    """Updates DynamoDB records for the given AMIs.

    Args:
        amis (list[dict]): List of AMI objects to update in DynamoDB.
    """
    scan_items = scan_ami_ddb_records(AMI_DDB_TABLE)

    for table_item in scan_items:
        ami_entry = get_ami(amis, table_item['ResourceId']['S'])

        # If Table Item is in ami list - Already accounted for in Table: Remove from ami list 
        # (don't need to add it to table - already tagged)
        if ami_entry is not None:
            # Check if ami has any configuration changes
            if table_item['Tags']['S'] != json.dumps(ami_entry['Tags']) \
              or table_item['AmiName']['S'] != ami_entry['Name'] \
              or table_item['ResourceState']['S'] != ami_entry['State'] \
              or table_item['Description']['S'] != ami_entry['Description'] \
              or table_item['LastLaunchedTime']['S'] != ami_entry['LastLaunchedTime'] \
              or table_item['BlockMappings']['S'] != json.dumps(ami_entry['BlockMappings']):
                print('updating:', table_item['ResourceId']['S'])
                update_ami_ddb_record(ami_entry)

            # Check if ami has deletion tag and if it is accurate
            deletion_tag_value = check_resource_for_deletion_tag(ami_entry)
            if deletion_tag_value is None or deletion_tag_value != table_item['DeletionDate']['S']:
                print('Tagging: ', table_item['ResourceId']['S'], " in account:", table_item['AccountName']['S'], "with ddb deletion date of ", table_item['DeletionDate']['S'])
                tag_resource(ami_entry['ResourceId'], ami_entry['AccountId'], ami_entry['Region'], ami_entry['Environment'], table_item['DeletionDate']['S'])

            # Since ami is already accounted for and updated, delete from new ami list
            amis = [obj for obj in amis if obj.get('ResourceId') != table_item['ResourceId']['S']]
        else:
            try:
                print(f"Item in DDB table is not in current ami list: {table_item['ResourceId']['S']}, needs to be removed from DDB table")

                ami_search = get_ami_by_id(table_item['ResourceId']['S'], table_item['AccountId']['S'], table_item['AccountName']['S'], table_item['ResourceRegion']['S'])
                if ami_search == []:
                    remove_ami_ddb_record(table_item['ResourceId']['S'])
                
                # As an inventory function, selective searching removes the requirement for this.
                # if ami_search != []:
                #   if (check_resource_for_deletion_tag(ami_search[0]) != None):
                #     untag_resource(table_item['ResourceId']['S'], table_item['AccountId']['S'], table_item['AccountName']['S'], table_item['ResourceRegion']['S'])
                # else:
                #   remove_ami_ddb_record(table_item['ResourceId']['S'])

            except ClientError as e:
                error_message = f"Error in DynamoDB delete_item ({table_item['ResourceId']['S']}): {str(e)}"
                print(error_message)
                error_log.append(error_message)

    # Check if there amis in amis list that aren't in table - Indicates they are newly detached
    for new_ami in amis:
        create_ami_ddb_record(new_ami)
        tag_resource(new_ami['ResourceId'], new_ami['AccountId'], new_ami['Region'], new_ami['Environment'], "")

    return

def check_resource_for_deletion_tag(resource):
    """
    Check if a resource has a deletion tag.
    Args:
        resource (dict): The resource to check.
    Returns:
        str: The deletion date if found, or None if not.
    """
    tags = resource.get('Tags', [])
    for tag in tags:
        if tag['Key'] == 'identified_for_deletion':
            return tag['Value']

    return False

def tag_resource(ami_id, account_id, region_name, env, ddb_deletion_date):
    """
    Tag an AMI with a deletion date.
    Args:
        ami_id (str): The ID of the AMI to tag.
        account_id (str): The ID of the account where the AMI is located.
        region_name (str): The name of the region where the AMI is located.
        env (str): The environment where the AMI is located.
        ddb_deletion_date (str): The deletion date of the AMI.
    """
    if ddb_deletion_date == "":
        deletion_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d') if env != 'prod' else (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')
    else:
        deletion_date = ddb_deletion_date

    try:
        access_key, secret_access_key, session_token = assume_new_account_role(account_id)
        ec2_client = get_multi_account_ec2_client(access_key, secret_access_key, session_token, region_name)
        ec2_client.create_tags(
            Resources=[
                ami_id,
            ],
            Tags=[
                {
                    'Key': 'identified_for_deletion',
                    'Value': deletion_date,
                },
            ],
        )
    except ClientError as e:
        error_message = f"Error in tagging AMI ({ami_id}): {str(e)}"
        print(error_message)
        error_log.append(error_message)

    return

def get_ami_by_id(ami_id, account_id, account_name, region):
    """
    Get AMI by ID in a specific account and region.
    Args:
        ami_id (str): The ID of the AMI.
        account_id (str): The ID of the account where the AMI is located.
        account_name (str): The name of the account where the AMI is located.
        region (str): The region where the AMI is located.
    Returns:
        list[dict]: A list of AMI information dictionaries.
    """
    ami_list_output = []

    try:
        access_key, secret_access_key, session_token = assume_new_account_role(account_id)
        ec2_client = get_multi_account_ec2_client(access_key, secret_access_key, session_token, region)

        # Get ami info
        response = ec2_client.describe_images(ImageIds=[ami_id])
        ami_list_output = response['Images']

    except ClientError as e:
        error_message = f"Error in finding AMI ({ami_id} in {account_id}, {account_name} - {region}): {str(e)}"
        print(error_message)
        error_log.append(error_message)

    return ami_list_output

def untag_resource(ami_id, account_id, region):
    """
    Remove tags from an AMI.
    Args:
        ami_id (str): The ID of the AMI.
        account_id (str): The ID of the account where the AMI is located.
        region (str): The region where the AMI is located.
    """
    try:
        access_key, secret_access_key, session_token = assume_new_account_role(account_id)
        ec2_client = get_multi_account_ec2_client(access_key, secret_access_key, session_token, region)

        ec2_client.delete_tags(
            Resources=[
                ami_id,
            ],
            Tags=[
                {
                    'Key': 'identified_for_deletion'
                },
            ]
        )
    except ClientError as e:
        error_message = f"Error in removing tags from AMI ({ami_id}): {str(e)}"
        print(error_message)
        error_log.append(error_message)

    return

def publish_sns_topic(subject_message, sns_input):
    """Publish a message to an SNS topic.

    Args:
        subject_message (str): The subject of the SNS message.
        sns_input (str): The input message for the SNS topic.
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
        print("Encountered Unknown Error when publishing to SNS Topic", SNSTOPICARN, " in AMI Inventory Lambda: ", e)
        raise
    return

def lambda_handler(event, context):
    """
    Lambda function to handle AMI inventory.
    Args:
        event (dict): The event data.
        context (dict): The context object.
    Returns:
        dict: The response from the Lambda function.
    """
    print("Event: ", event, "Context: ", context)
    amis = []
    account_list = get_active_accounts()
    for account in account_list:
        if account['AccountStatus']['S'] == "ACTIVE" :
            access_key, secret_access_key, session_token = assume_new_account_role(account['AccountId']['S'])
            associated_regions = REGIONS
            amis.extend(get_amis(account['AccountId']['S'], account['AccountName']['S'], account['Environment']['S'], associated_regions, access_key, secret_access_key, session_token))

    print('Total AMIs:', len(amis))
    update_ddb_records(amis)

    if error_log:
        message = ""
        for error in error_log:
            message += error + ",\n"
        print(message)
        publish_sns_topic('AMI Inventory Issues', message)

    return {
        'statusCode': 200,
        'body': 'AMI Inventory Completed Successfully'
    }
