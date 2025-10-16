"""
EBS Snapshot Inventory Lambda Function.  
Gathers EBS snapshot data from all accounts and regions and stores it in a DynamoDB table.
Deletion date is set to establish a time to live for each snapshot based on environment tag.
"""
import os
from datetime import datetime, timedelta, timezone
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
import botocore

AWS_REGION = os.environ['AWS_REGION']
CROSS_ACCOUNT_ROLE = os.environ['CROSS_ACCOUNT_ROLE']
ACTIVE_REGIONS = os.environ['ACTIVE_REGIONS'].split(',')
ACCOUNT_DDB_TABLE = os.environ['ACCOUNT_TABLE']
ACCOUNT_DDB_TABLE_INDEX = 'AccountName-index'
DELETION_TABLE = os.environ['SNAPSHOT_DELETION_TABLE']
SNSTOPICARN=os.environ['SNS_ARN']
EBS_SNAPSHOT_PRICING = {
    'us-west-2': {
      'standard': 0.05,
      'archive': 0.0125
    },
    'us-east-1': {
        'standard': 0.05,
        'archive': 0.0125
    },
    'eu-west-1': {
        'standard': 0.05,
        'archive': 0.0125
    },
    'eu-west-2': {
        'standard': 0.053,
        'archive': 0.01325
    },
    'eu-central-1': {
        'standard': 0.054,
        'archive': 0.0135
    },
    'ap-southeast-1': {
        'standard': 0.05,
        'archive': 0.0125
    }
  }

config = Config(
  retries = {
      'max_attempts': 2,
      'mode': 'standard'
  }
)

today_date = datetime.now().strftime('%Y-%m-%d')
ninety_days_ago = datetime.now() - timedelta(days=90)
thirty_days_ago = datetime.now() - timedelta(days=30)

error_log = []

def get_active_accounts():
    """
    Get active accounts from DynamoDB.
    Returns:
        list: A list of active account information.
    """
    try:
        dynamodb_client = boto3.client('dynamodb')
        scan_response = dynamodb_client.scan(TableName=ACCOUNT_DDB_TABLE)
        return scan_response['Items']

    except ClientError as e:
        error_message = f"Error in {ACCOUNT_DDB_TABLE} DynamoDB scan and processing: {str(e)}"
        print(error_message)
        error_log.append(error_message)

    return

def assume_new_account_role(account_id):
    """
    Assume a new role in a different AWS account.
    Args:
        account_id (str): The ID of the account to assume the role in.
    Returns:
        tuple: A tuple containing the access key, secret access key, and session token.
    """
    sts_connection = boto3.client('sts')
    acct_connection = sts_connection.assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/{CROSS_ACCOUNT_ROLE}",
        RoleSessionName="cross_account_lambda"
    )

    access_key = acct_connection['Credentials']['AccessKeyId']
    secret_access_key = acct_connection['Credentials']['SecretAccessKey']
    session_token = acct_connection['Credentials']['SessionToken']

    return access_key, secret_access_key, session_token

def get_multi_account_ec2_client(access_key, secret_access_key, session_token, region):
    """
    Get an EC2 client for a specific AWS account and region.
    Args:
        access_key (str): Access key for the assumed role session.
        secret_access_key (str): Secret access key for the assumed role session.
        session_token (str): Session token for the assumed role session.
        region (str): The AWS region to create the EC2 client for.
    """
    ec2_client = boto3.client('ec2', aws_access_key_id=access_key, aws_secret_access_key=secret_access_key, aws_session_token=session_token, region_name=region)

    return ec2_client

def get_snapshots(ec2_client, account_id, account_name, env, region):
    """
    Get EBS snapshots for a specific account and region.

    Args:
        ec2_client (boto3.client): EC2 client for the specific account and region.
        account_id (str): The ID of the AWS account.
        account_name (str): The name of the AWS account.
        env (str): The environment (e.g., prod, dev).
        region (str): The AWS region.

    Returns:
        list: A list of EBS snapshots.
    """
    old_snapshots = []
    days_threshold = 90 if env == 'prod' else 30
    cutoff_date = (datetime.utcnow() - timedelta(days=days_threshold)).replace(tzinfo=timezone.utc)

    try:
        snapshots_response = ec2_client.describe_snapshots(
            OwnerIds=['self']
        )

        for snapshot in snapshots_response['Snapshots']:
            description = snapshot['Description']
            ami_data = description[len(snapshot['Description']) - 21:] if description.startswith("Created by CreateImage(") else ""

            start_time = snapshot['StartTime']
            if start_time <= cutoff_date:
                old_snapshots.append({
                    'SnapshotId': snapshot['SnapshotId'],
                    'AccountId': account_id,
                    'AccountName': account_name,
                    'Description': snapshot['Description'],
                    'Environment': env,
                    'Region': region,
                    'StartTime': start_time.date(),
                    'State': snapshot['State'],
                    'VolumeSize': snapshot['VolumeSize'],
                    'StorageTier': snapshot.get('StorageTier', 'standard'),
                    'MonthlyCost': get_ebs_snapshot_cost(
                      region, snapshot.get('StorageTier', 'standard'), snapshot['VolumeSize']
                    ),
                    'Tags': snapshot.get('Tags', []),
                    'ExceptionFlag': "False",
                    'ConnectedResource': ami_data
                })

    except ClientError as e:
        error_message = f"Error getting snapshots for account {account_id} in region {region}: {e}"
        error_log.append(error_message)
    # Optionally, handle other specific exceptions here if needed
    # For now, only ClientError is caught above.

    return old_snapshots

def get_ebs_snapshot_cost(region, storage_tier, volume_size):
    """
    Get the estimated monthly cost of an EBS snapshot.
    Args:
        region (str): The AWS region where the snapshot is located.
        storage_tier (str): The storage tier of the snapshot (e.g., standard, gp2, gp3).
        volume_size (int): The size of the volume in GB.
    Raises:
        ValueError: If the region is not found in the pricing information.
    Returns:
        str: The estimated monthly cost of the snapshot.
    """
    if region in EBS_SNAPSHOT_PRICING:
        storage_rate = EBS_SNAPSHOT_PRICING[region].get(storage_tier, 0)
        snapshot_cost = volume_size * storage_rate
        return f"{snapshot_cost:.2f}"
    else:
        error_log.append(f"Region {region} not found in EBS Snapshot Pricing")
        raise ValueError(f"Region {region} not found in EBS Snapshot Pricing")

def tag_old_snapshots(old_snapshots, ec2_client):
    """Tag old EBS snapshots for deletion.

    Args:
        old_snapshots (list[dict]): List of old snapshot dictionaries.
        ec2_client (boto3.client): Boto3 EC2 client.
    """
    for snapshot in old_snapshots:
        deletion_date = calculate_deletion_date(snapshot)

        try:
            # Check if the snapshot already has the 'identified_for_deletion' tag
            if not has_identified_for_deletion_tag(snapshot):
                ec2_client.create_tags(
                    Resources=[snapshot['SnapshotId']],
                    Tags=[{'Key': 'identified_for_deletion', 'Value': deletion_date}]
                )
                print(f'Successfully tagged snapshot {snapshot["SnapshotId"]}')

        except ClientError as e:
            error_message = f'Error tagging snapshot {snapshot["SnapshotId"]}: {e}'
            print(error_message)
            error_log.append(error_message)

def calculate_deletion_date(snapshot):
    """
    Calculate the deletion date for an EBS snapshot.
    Args:
        snapshot (dict): The snapshot dictionary containing metadata.
    Returns:
        str: The calculated deletion date in 'YYYY-MM-DD' format.
    """
    if snapshot['Environment'] == 'prod':
        if snapshot['StartTime'] <= ninety_days_ago.date():
            return '2025-01-16'
        else:
            return (snapshot['StartTime'] + timedelta(days=90)).strftime('%Y-%m-%d')
    elif snapshot['Environment'] != 'prod':
        if snapshot['StartTime'] <= thirty_days_ago.date():
            return '2024-11-17'
        else:
            return (snapshot['StartTime'] + timedelta(days=30)).strftime('%Y-%m-%d')
    return today_date

def has_identified_for_deletion_tag(snapshot):
    """
    Check if the snapshot has the 'identified_for_deletion' tag.
    Args:
        snapshot (dict): The snapshot dictionary containing metadata.
    Returns:
        bool: True if 'identified_for_deletion' tag exists, False otherwise.
    """
    tags = snapshot.get('Tags', [])
    return any(tag['Key'] == 'identified_for_deletion' for tag in tags)

def get_snapshot_from_list(snapshots, snapshot_id):
    """
    Get a snapshot from a list of snapshots by its ID.
    Args:
        snapshots (list[dict]): The list of snapshot dictionaries.
        snapshot_id (str): The ID of the snapshot to retrieve.
    Returns:
        dict: The snapshot dictionary if found, None otherwise.
    """
    for snapshot in snapshots:
        if snapshot['SnapshotId'] == snapshot_id:
            return snapshot
    return None

def get_snapshot_ddb_record(snapshot_id):
    """Get a snapshot record from DynamoDB.

    Args:
        snapshot_id (str): The ID of the snapshot to retrieve.

    Returns:
        dict: The snapshot record if found, None otherwise.
    """
    try:
        primary_session = boto3.Session()
        dynamodb_client = primary_session.client('dynamodb')

        response = dynamodb_client.get_item(
            Key={
                'ResourceId': {
                    'S': snapshot_id,
                },
            },
            TableName=DELETION_TABLE,
        )

        return response

    except ClientError as e:
        error_message = f"Error in {DELETION_TABLE} DynamoDB scan and processing: {str(e)}"
        print(error_message)
        error_log.append(error_message)

def scan_snapshot_ddb_records(table_name):
    """Scan all records in the specified DynamoDB table.

    Args:
        table_name (str): The name of the DynamoDB table to scan.

    Returns:
        dict: The scan response from DynamoDB.
    """
    scan_response = {}

    try:
        primary_session = boto3.Session()
        dynamodb_client = primary_session.client('dynamodb')
        scan_response = dynamodb_client.scan(TableName=table_name)
    except ClientError as e:
        error_message = f"Error in DynamoDB scan: {str(e)}"
        print(error_message)

    return scan_response

def create_snapshot_ddb_record(snapshot):
    """
    Create a new EBS Snapshot record in the DynamoDB table.
    Args:
        snapshot (dict): The snapshot data to store in the DDB table.
    """

    try:
        primary_session = boto3.Session()
        dynamodb_client = primary_session.client('dynamodb')

        dynamodb_client.update_item(
            Key={
                'ResourceId': {
                    'S': snapshot['SnapshotId'],
                }
            },
            UpdateExpression="SET AccountId = :accountId, DeletionDate = :date, \
                ExceptionFlag = :exception, AccountName = :accountName, \
                ResourceRegion = :region, ResourceState = :state, StorageTier = :storageTier, \
                VolumeSize = :volumeSize, MonthlyCost = :monthlyCost, \
                ConnectedResource = :connectedResource, LastUpdated = :lastUpdated",
            ConditionExpression="attribute_not_exists(ResourceId)",
            ExpressionAttributeValues={
              ':accountId': {'S': snapshot['AccountId']},
              ':date': {'S': calculate_deletion_date(snapshot)},
              ':exception': {'S': snapshot['ExceptionFlag']},
              ':accountName': {'S': snapshot['AccountName']},
              ':region': {'S': snapshot['Region']},
              ':state': {'S': snapshot['State']},
              ':storageTier': {'S': snapshot['StorageTier']},
              ':volumeSize': {'N': str(snapshot['VolumeSize'])},
              ':monthlyCost': {'N': snapshot['MonthlyCost']},
              ':connectedResource': {'S': snapshot['ConnectedResource']},
              ':lastUpdated': {'S': today_date}
            },
            TableName=DELETION_TABLE,
        )
    except ClientError as e:
        error_message = f"Error in DynamoDB update_item ({snapshot['SnapshotId']}): {str(e)}"
        print(error_message)

def remove_snapshot_ddb_record(snapshot_id):
    """
    Remove EBS snapshot record from DynamoDB table.
    Args:
        snapshot_id (str): The ID of the snapshot to remove.
    """

    try:
        primary_session = boto3.Session()
        dynamodb_client = primary_session.client('dynamodb')

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

    return

def update_snapshot_ddb_record(snapshot):
    # Updates EBS snapshot record in ddb table
    # Parameters:
    #     snapshot (obj): Snapshot object to update a DDB entry from
    # Returns:
    #     None
    try:
        primary_session = boto3.Session()
        dynamodb_client = primary_session.client('dynamodb')

        # Add to table
        dynamodb_client.update_item(
            Key={
                'ResourceId': {
                    'S': snapshot['SnapshotId'],
                }
            },
            UpdateExpression="SET ResourceState = :state, VolumeSize = :volumeSize, StorageTier = :storageTier, MonthlyCost = :monthlyCost",
            ExpressionAttributeValues={
                ':state': {'S': snapshot['State']},
                ':storageTier': {'S': snapshot['StorageTier']},
                ':volumeSize': {'N': str(snapshot['VolumeSize'])},
                ':monthlyCost': {'N': snapshot['MonthlyCost']}
            },
            TableName=DELETION_TABLE,
        )
    except ClientError as e:
        error_message = f"Error in DynamoDB update_item ({snapshot['SnapshotId']}): {str(e)}"
        print(error_message)
        error_log.append(error_message)

def update_ddb_records(snapshots):
    """
    Update DynamoDB records for EBS snapshots.
    Args:
        snapshots (list): List of snapshot dictionaries to update in DynamoDB.
    """
    scan_response = scan_snapshot_ddb_records(DELETION_TABLE)

    for table_item in scan_response['Items']:
        snapshot_entry = get_snapshot_from_list(snapshots, table_item['ResourceId']['S'])

        # If Table Item is in snapshot list - Already accounted for in Table: 
        # Remove from snapshot list (don't need to add it to table - already tagged)
        if snapshot_entry != None:

            # Check if EBS snapshot has any configuration changes
            if table_item['ResourceState']['S'] != snapshot_entry['State'] or table_item['VolumeSize']['N'] != str(snapshot_entry['VolumeSize']) or table_item['StorageTier']['S'] != str(snapshot_entry['StorageTier']) or f"{float(table_item['MonthlyCost']['N']):.2f}" != str(snapshot_entry['MonthlyCost']):
                print('updating:', table_item['ResourceId']['S'])
                update_snapshot_ddb_record(snapshot_entry)

            # Check if EBS snapshot has deletion tag and if it is accurate
            deletion_tag_value = check_snapshot_for_deletion_tag(snapshot_entry)
            if deletion_tag_value == None or deletion_tag_value != table_item['DeletionDate']['S']:
                print('Tagging: ', table_item['ResourceId']['S'], " in account:", \
                    table_item['AccountName']['S'], "with ddb deletion date of ", \
                    table_item['DeletionDate']['S'], "instead of", deletion_tag_value)
                tag_snapshot(snapshot_entry['SnapshotId'], snapshot_entry['AccountId'], \
                    snapshot_entry['Region'], table_item['DeletionDate']['S'])

            # Since snapshot is already accounted for and updated, delete from snapshots list
            snapshots = [obj for obj in snapshots if obj.get('SnapshotId') != table_item['ResourceId']['S']]
        else:
            try:
                print(f"Item in DDB table not in current snapshots list: {table_item['ResourceId']['S']}, needs to be removed from DDB table")

                snapshot_search = get_snapshot_by_id(table_item['ResourceId']['S'], \
                    table_item['AccountId']['S'], table_item['AccountName']['S'], table_item['ResourceRegion']['S'])           ######## CHECK RETURNS
                if snapshot_search == []:
                    print("removing snapshot", table_item['ResourceId']['S'], "from ddb table")
                    remove_snapshot_ddb_record(table_item['ResourceId']['S'])
            except ClientError as e:
                error_message = f"Error in DynamoDB delete_item ({table_item['ResourceId']['S']}): {str(e)}"
                print(error_message)

    for new_snapshot in snapshots:
        print("New Snapshot:", new_snapshot['SnapshotId'], new_snapshot['AccountId'], \
            new_snapshot['Region'], new_snapshot['Environment'])
        create_snapshot_ddb_record(new_snapshot)
        tag_snapshot(new_snapshot['SnapshotId'], new_snapshot['AccountId'], \
            new_snapshot['Region'], calculate_deletion_date(new_snapshot))
    return

def check_string_in_array_of_objects(array, string_to_check):
    """
    Check if a string is present in an array of objects.
    Args:
        array (list): List of objects to search.
        string_to_check (str): String to find in the objects.
    Returns:
        bool: True if the string is found, False otherwise.
    """

    for obj in array:
        if obj['ResourceId'] == string_to_check:
            return True
    return False

def check_snapshot_for_deletion_tag(snapshot):
    """
    Check if the snapshot has a deletion tag.
    Args:
        snapshot (dict): The snapshot object to check.
    Returns:
        str: The deletion date if found, None otherwise.
    """
    tags = snapshot.get('Tags', [])
    for tag in tags:
        if tag['Key'] == 'identified_for_deletion':
            return tag['Value']
    return None

def tag_snapshot(snapshot_id, account_id, region_name, deletion_date):
    """
    Tag an EBS snapshot with a deletion date.
    Args:
        snapshot_id (str): The ID of the snapshot to tag.
        account_id (str): The ID of the account where the snapshot exists.
        region_name (str): The name of the region where the snapshot exists.
        deletion_date (str): The date the snapshot is to be deleted.
    """
    try:
        access_key, secret_access_key, session_token = assume_new_account_role(account_id)
        ec2_client = get_multi_account_ec2_client(access_key, \
            secret_access_key, session_token, region_name)
        ec2_client.create_tags(
            Resources=[
                snapshot_id,
            ],
            Tags=[
                {
                    'Key': 'identified_for_deletion',
                    'Value': deletion_date,
                },
            ],
        )
    except ClientError as e:
        error_message = f"Error in tagging EBS snapshot ({snapshot_id}): {str(e)}"
        print(error_message)

    return

def get_snapshot_by_id(snapshot_id, account_id, account_name, region):
    """
    Get EBS Snapshot by ID
    Args:
        snapshot_id (str): The ID of the snapshot to retrieve.
        account_id (str): The ID of the account where the snapshot exists.
        account_name (str): The name of the account where the snapshot exists.
        region (str): The region where the snapshot exists.
    Returns:
        list: A list containing the snapshot information, or an empty list if not found.
    """
    snapshot_list_output = []

    try:
        access_key, secret_access_key, session_token = assume_new_account_role(account_id)
        ec2_client = get_multi_account_ec2_client(access_key, secret_access_key, session_token, region)

        response = ec2_client.describe_snapshots(SnapshotIds=[snapshot_id])
        snapshot_list_output = response['Snapshots']

    except ClientError as e:
        error_message = f"Error in finding EBS Snapshot ({snapshot_id} in {account_id}, {account_name} - {region}): {str(e)}"
        print(error_message)
        error_log.append(error_message)

    return snapshot_list_output

def publish_sns_topic(subject_message, sns_input):
    """
    Publish a message to an SNS topic.
    Args:
        subject_message (str): The subject of the SNS message.
        sns_input (str): The message body for the SNS topic.
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
        print("Encountered Unknown Error when publishing to SNS Topic", \
            SNSTOPICARN, " in Validation Lambda: ", e)
        raise
    return

def lambda_handler(event, context):
    """
    Lambda function to handle EBS snapshot inventory.
    Args:
        event (dict): The event data passed to the Lambda function.
        context (LambdaContext): The context object containing runtime information.
    Returns:
        dict: The response object containing the status code and message.
    """
    print("Event: ", event, "Context: ", context)
    snapshot_list = []
    account_list = get_active_accounts()
    for account in account_list:
        try:
            # Validate keys before accessing them
            if account['AccountStatus']['S'] == "ACTIVE":
                account_id = account['AccountId']['S']
                account_name = account['AccountName']['S']
                environment = account['Environment']['S']
                access_key, secret_access_key, session_token = assume_new_account_role(account['AccountId']['S'])

                for region in ACTIVE_REGIONS:
                    ec2_client = get_multi_account_ec2_client(access_key, \
                        secret_access_key, session_token, region)
                    # Call function to get old snapshots
                    old_ebs_snapshots = get_snapshots(ec2_client, account_id, \
                        account_name, environment, region)
                    # Add old snapshots to list
                    snapshot_list.extend(old_ebs_snapshots)          

        except ClientError as e:
            error_message = f"ClientError with account {account.get('AccountId', 'unknown')}: {e}"
            error_log.append(error_message)
            continue  # Skip to the next account   
        except KeyError as e:
            error_message = f"KeyError with account {account.get('AccountId', 'unknown')}: {e}"
            error_log.append(error_message)
            continue  # Skip to the next account   

    print("Number of Snapshots to be deleted:", len(snapshot_list))

    update_ddb_records(snapshot_list)

    if error_log:
        message = ""
        for error in error_log:
            message += error + ",\n"
        print(message)
        publish_sns_topic('EBS Snapshot Inventory Issues', message)

    return {
          'statusCode': 200,
          'body': 'EBS Snapshot Inventory Completed Successfully'
    }
