"""
Lambda Function Creates and Inventory of detached EBS Volumes
"""
import os
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError
import botocore

AWS_REGION = os.environ['AWS_REGION']
CROSS_ACCOUNT_ROLE = os.environ['CROSS_ACCOUNT_ROLE']
ACTIVE_REGIONS = os.environ['ACTIVE_REGIONS'].split(',')
CORE_ACCOUNTS = []

ACCOUNT_DDB_TABLE = os.environ['ACCOUNT_TABLE']  # 'aws-accounts'
ACCOUNT_DDB_TABLE_INDEX = 'AccountName-index'
EBS_VOLUME_DDB_TABLE = os.environ['EBS_VOLUME_TABLE'] # 'detached-ebs-volumes'

SNSTOPICARN=os.environ['SNS_ARN']

# Constants for EBS pricing based on region
EBS_PRICING = {
    'us-west-2': {
        'gp3': {
            'price_per_gb_month' : 0.08,  # General Purpose SSD (gp3) storage per GB-month
            'iops_price_per_unit' : 0.005, # Provisioned IOPS SSD (io1) IOPS per IOPS-month
            'throughput_per_unit' : 0.040 # Provisioned throughput SSD (io1) IOPS per IOPS-month
        },
        'gp2': {'price_per_gb_month': 0.10},  # General Purpose SSD (gp2) volumes per GB-month
        'io1': {
            'price_per_gb_month': 0.125, 
            'iops_price_per_unit': 0.065
        }, # Provisioned IOPS SSD (io1) volumes per GB-month
        'io2': {
            'price_per_gb_month': 0.125, 
            'iops_price_per_unit_under_32000': 0.065,
            'iops_price_per_unit_under_64000': 0.046,
            'iops_price_per_unit_over_64000': 0.032
        },
        'standard': {'price_per_gb_month': 0.045}, # Throughput Optimized HDD (st1) per GB-month
        'sc1': {'price_per_gb_month': 0.015} # Cold HDD (sc1) volumes per GB-month
    },
    'us-east-1': {
        'gp3': {
            'price_per_gb_month' : 0.08,  # General Purpose SSD (gp3) storage per GB-month
            'iops_price_per_unit' : 0.005, # Provisioned IOPS SSD (io1) IOPS per IOPS-month
            'throughput_per_unit' : 0.040 # Provisioned throughput SSD (io1) IOPS per IOPS-month
        },
        'gp2': {'price_per_gb_month': 0.10},  # General Purpose SSD (gp2) per GB-month
        'io1': {
            'price_per_gb_month': 0.125, 
            'iops_price_per_unit': 0.065          
        }, # Provisioned IOPS SSD (io1) per GB-month
        'io2': {
            'price_per_gb_month': 0.125, 
            'iops_price_per_unit_under_32000': 0.065,
            'iops_price_per_unit_under_64000': 0.046,
            'iops_price_per_unit_over_64000': 0.032
        },
        'standard': {'price_per_gb_month': 0.045}, # Throughput Optimized HDD (st1) per GB-month
        'sc1': {'price_per_gb_month': 0.015} # Cold HDD (sc1) per GB-month
    },
    'eu-west-1': {
        'gp3': {
            'price_per_gb_month': 0.088,  # General Purpose SSD (gp3) per GB-month
            'iops_price_per_unit': 0.0055, # Provisioned IOPS SSD (io1) per IOPS-month
            'throughput_per_unit' : 0.044 # Provisioned throughput SSD (io1) IOPS per IOPS-month
        },
        'gp2': {'price_per_gb_month': 0.11},  # General Purpose SSD (gp2) per GB-month
        'io1': {
            'price_per_gb_month': 0.138,
            'iops_price_per_unit': 0.0072
        }, # Provisioned IOPS SSD (io1) per GB-month
        'io2': {
            'price_per_gb_month': 0.138, 
            'iops_price_per_unit_under_32000': 0.072,
            'iops_price_per_unit_under_64000': 0.050,
            'iops_price_per_unit_over_64000': 0.035
        },
        'standard': {'price_per_gb_month': 0.05}, # Throughput Optimized HDD (st1) per GB-month
        'sc1': {'price_per_gb_month': 0.0168} # Cold HDD (sc1) per GB-month
    },
    'eu-west-2': {
        'gp3': {
            'price_per_gb_month': 0.0928,  # General Purpose SSD (gp3) per GB-month
            'iops_price_per_unit': 0.0058, # Provisioned IOPS SSD (io1) per IOPS-month
            'throughput_per_unit' : 0.046 # Provisioned throughput SSD (io1) IOPS per IOPS-month
        },
        'gp2': {'price_per_gb_month': 0.116},  # General Purpose SSD (gp2) per GB-month
        'io1': {
            'price_per_gb_month': 0.149,
            'iops_price_per_unit': 0.0076
        }, # Provisioned IOPS SSD (io1) per GB-month
        'io2': {
            'price_per_gb_month': 0.145, 
            'iops_price_per_unit_under_32000': 0.076,
            'iops_price_per_unit_under_64000': 0.053,
            'iops_price_per_unit_over_64000': 0.037
        },
        'standard': {'price_per_gb_month': 0.053}, # Throughput Optimized HDD (st1) per GB-month
        'sc1': {'price_per_gb_month': 0.0174} # Cold HDD (sc1) per GB-month
    },
    'eu-central-1': {
        'gp3': {
            'price_per_gb_month': 0.0952,  # General Purpose SSD (gp3) per GB-month
            'iops_price_per_unit': 0.006, # Provisioned IOPS SSD (io1) per IOPS-month,
            'throughput_per_unit' : 0.048 # Provisioned throughput SSD (io1) IOPS per IOPS-month
        },
        'gp2': {'price_per_gb_month': 0.119},  # General Purpose SSD (gp2) per GB-month
        'io1': {
            'price_per_gb_month': 0.149,
            'iops_price_per_unit': 0.0078
        }, # Provisioned IOPS SSD (io1) per GB-month
        'io2': {
            'price_per_gb_month': 0.149, 
            'iops_price_per_unit_under_32000': 0.078,
            'iops_price_per_unit_under_64000': 0.055,
            'iops_price_per_unit_over_64000': 0.038
        },
        'standard': {'price_per_gb_month': 0.054}, # Throughput Optimized HDD (st1) per GB-month
        'sc1': {'price_per_gb_month': 0.018} # Cold HDD (sc1) per GB-month
    },
    'ap-southeast-1': {
        'gp3': {
            'price_per_gb_month': 0.096,  # General Purpose SSD (gp3) per GB-month
            'iops_price_per_unit': 0.006, # Provisioned IOPS SSD (io1) per IOPS-month
            'throughput_per_unit' : 0.048 # Provisioned throughput SSD (io1) IOPS per IOPS-month
        },
        'gp2': {'price_per_gb_month': 0.12},  # General Purpose SSD (gp2) per GB-month
        'io1': {
            'price_per_gb_month': 0.138,
            'iops_price_per_unit': 0.0072
        }, # Provisioned IOPS SSD (io1) per GB-month
        'io2': {
            'price_per_gb_month': 0.138, 
            'iops_price_per_unit_under_32000': 0.072,
            'iops_price_per_unit_under_64000': 0.050,
            'iops_price_per_unit_over_64000': 0.035
        },
        'standard': {'price_per_gb_month': 0.054}, # Throughput Optimized HDD (st1) per GB-month
        'sc1': {'price_per_gb_month': 0.018} # Cold HDD (sc1) per GB-month
    }
    # Add other regions as needed
}

error_log = []

def get_active_accounts():
    """Retrieve active accounts from the DynamoDB table.

    Returns:
        list: A list of active account items from the DynamoDB table.
    """
    try:
        dynamodb_client = boto3.client('dynamodb', region_name = 'us-west-2')
        scan_response = dynamodb_client.scan(TableName=ACCOUNT_DDB_TABLE)
        return scan_response['Items']

    except ClientError as e:
        error_message = f"Error in {ACCOUNT_DDB_TABLE} DynamoDB scan and processing: {str(e)}"
        print(error_message)
        error_log.append(error_message)

    return

def assume_new_account_role(account_id):
    """
    Assume a role in a new AWS account.
    Args:
        account_id (str): The ID of the account to assume the role in.
    Returns:
        tuple: A tuple containing the access key, secret access key, 
            and session token for the assumed role.
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
    Create an EC2 client for a specific AWS region.
    Args:
        access_key (str): Access key for cross-account role session.
        secret_access_key (str): Secret access key for cross-account role session.
        session_token (str): Session token for cross-account role session.
        region (str): AWS region for the EC2 client.
    Returns:
        boto3.client: Boto3 EC2 client for the specified region.
    """
    ec2_client = boto3.client('ec2', aws_access_key_id=access_key, \
        aws_secret_access_key=secret_access_key, aws_session_token=session_token, \
        region_name=region)

    return ec2_client

def get_detached_volumes(account_id, account_name, env, regions, access_key, secret_access_key, session_token):
    """
    Retrieve detached EBS volumes for a specific account.
    Args:
        account_id (str): The ID of the AWS account.
        account_name (str): The name of the AWS account.
        env (str): The environment (e.g., production, staging).
        regions (list): A list of AWS regions to check for detached volumes.
        access_key (str): The access key for the AWS account.
        secret_access_key (str): The secret access key for the AWS account.
        session_token (str): The session token for the AWS account.
    Returns:
        list: A list of detached EBS volumes for the specified account.
    """
    detached_volumes = []

    date_diff_30_days = datetime.now() + timedelta(days=30)
    thirty_days_date = (datetime(date_diff_30_days.year, date_diff_30_days.month, date_diff_30_days.day)).strftime('%Y-%m-%d')
    date_diff_90_days = datetime.now() + timedelta(days=90)
    ninety_days_date = (datetime(date_diff_90_days.year, date_diff_90_days.month, date_diff_90_days.day)).strftime('%Y-%m-%d')

    for region in regions:
        detached_volume_list_output = []
        try:
            print(f'Getting detached EBS Volumes for account {account_name} in region {region}')
            ec2_client = get_multi_account_ec2_client(access_key, secret_access_key, session_token, region)

            # Get initial detached volumes list
            response = ec2_client.describe_volumes(Filters=[{'Name': 'status','Values': ['available',]}],MaxResults=20)
            detached_volume_list_output = response['Volumes']

            # Loop describe_volumes until all detached volumes are added to the detached_volume_list_output
            while 'NextToken' in response:
                response = ec2_client.describe_volumes(Filters=[{'Name': 'status','Values': ['available',]}], MaxResults=20, NextToken=response['NextToken'])
                detached_volume_list_output.extend(response['Volumes'])

        except ClientError as e:
            error_message = f"Error for {account_name} in {region}: {str(e)}"
            print(error_message)
            error_log.append(error_message)

        # Create a new list of detached volumes from the list of describe_volumes responses with relevant data
        for detached_volume in detached_volume_list_output:
            if detached_volume['Attachments'] == []:
                deletion_date = ninety_days_date if env == 'prod' else thirty_days_date
                throughput = 0 if detached_volume['VolumeType'] != 'gp3' else detached_volume['Throughput']
                detached_volumes.append({'VolumeId': detached_volume['VolumeId'], 'AccountName': account_name, \
                    'AccountId': account_id, 'Environment': env, 'Region': region, 'State': 'Detached', \
                    'Date': deletion_date, 'Exception': 'False', 'VolumeType': detached_volume['VolumeType'], \
                    'VolumeSize': detached_volume['Size'], 'VolumeIops': detached_volume.get('Iops', 0), \
                    'VolumeThroughput': throughput, 'Tags': detached_volume.get('Tags', [])})

    return detached_volumes

def get_detached_volume(detached_volumes, volume_id):
    """
    Get a detached volume by its ID.
    Args:
        detached_volumes (list): List of detached volumes.
        volume_id (str): The ID of the volume to retrieve.
    Returns:
        dict: The detached volume with the specified ID, or None if not found.
    """
    for detached_volume in detached_volumes:
        if detached_volume['VolumeId'] == volume_id:
            return detached_volume

    return None

def get_ebs_volume_ddb_record(volume_id):
    """
    Get an EBS volume record from DynamoDB.
    Args:
        volume_id (str): The ID of the volume to retrieve.
    Returns:
        dict: The EBS volume record from DynamoDB, or None if not found.
    """
    try:
        primary_session = boto3.Session()
        dynamodb_client = primary_session.client('dynamodb')

        response = dynamodb_client.get_item(
            Key={
                'VolumeId': {
                    'S': volume_id,
                },
            },
            TableName=EBS_VOLUME_DDB_TABLE,
        )
        return response

    except ClientError as e:
        error_message = f"Error in {ACCOUNT_DDB_TABLE} DynamoDB scan and processing: {str(e)}"
        print(error_message)
        error_log.append(error_message)

def scan_ebs_volume_ddb_records(table_name):
    """
    Scan all EBS volume records in the specified DynamoDB table.
    Args:
        table_name (str): The name of the table to scan.
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
        error_log.append(error_message)

    return scan_response

def remove_ebs_volume_ddb_record(volume_id):
    """
    Remove EBS Volume record from DynamoDB.
    Args:
        volume_id (str): The ID of the volume to remove.
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
        error_message = f"Error in {EBS_VOLUME_DDB_TABLE} DynamoDB scan and processing: {str(e)}"
        print(error_message)
        error_log.append(error_message)

    return

def create_ebs_volume_ddb_record(detached_volume):
    """
    Create an EBS volume record in DynamoDB.
    Args:
        detached_volume (dict): The detached volume information.
    """
    try:
        primary_session = boto3.Session()
        dynamodb_client = primary_session.client('dynamodb')

        # Add to table
        dynamodb_client.update_item(
            Key={
                'VolumeId': {
                    'S': detached_volume['VolumeId'],
                }
            },
            UpdateExpression="SET AccountId = :accountId, DeletionDate = :date, \
                ExceptionFlag = :exception, AccountName = :accountName, \
                ResourceRegion = :region, ResourceState = :state, \
                VolumeType = :volumeType, VolumeSize = :volumeSize, \
                VolumeIops = :volumeIops, VolumeThroughput = :volumeThroughput, \
                MonthlyCost = :monthlyCost",
            ConditionExpression="attribute_not_exists(VolumeId)",
            ExpressionAttributeValues={
                ':accountId': {'S': detached_volume['AccountId']},
                ':date': {'S': detached_volume['Date']},
                ':exception': {'S': detached_volume['Exception']},
                ':accountName': {'S': detached_volume['AccountName']},
                ':region': {'S': detached_volume['Region']},
                ':state': {'S': detached_volume['State']},
                ':volumeType': {'S': detached_volume['VolumeType']},
                ':volumeSize': {'N': str(detached_volume['VolumeSize'])},
                ':volumeIops': {'N': str(detached_volume['VolumeIops'])},
                ':volumeThroughput': {'N': str(detached_volume['VolumeThroughput'])},
                ':monthlyCost': {'N': detached_volume['MonthlyCost']}
            },
            TableName=EBS_VOLUME_DDB_TABLE,
        )

    except ClientError as e:
        error_message = f"Error in DynamoDB update_item ({detached_volume['VolumeId']}): {str(e)}"
        print(error_message)
        error_log.append(error_message)

def update_ebs_volume_ddb_record(detached_volume):
    """
    Update an existing EBS volume record in DynamoDB.
    Args:
        detached_volume (dict): The detached volume information.
    """
    try:
        primary_session = boto3.Session()
        dynamodb_client = primary_session.client('dynamodb')

        # Add to table
        dynamodb_client.update_item(
            Key={
                'VolumeId': {
                    'S': detached_volume['VolumeId'],
                }
            },
            UpdateExpression="SET VolumeType = :volumeType, \
                VolumeSize = :volumeSize, VolumeIops = :volumeIops, \
                VolumeThroughput = :volumeThroughput, MonthlyCost = :monthlyCost",
            ExpressionAttributeValues={
                ':volumeType': {'S': detached_volume['VolumeType']},
                ':volumeSize': {'N': str(detached_volume['VolumeSize'])},
                ':volumeIops': {'N': str(detached_volume['VolumeIops'])},
                ':volumeThroughput': {'N': str(detached_volume['VolumeThroughput'])},
                ':monthlyCost': {'N': detached_volume['MonthlyCost']}
            },
            TableName=EBS_VOLUME_DDB_TABLE,
        )

    except ClientError as e:
        error_message = f"Error in DynamoDB update_item ({detached_volume['VolumeId']}): {str(e)}"
        print(error_message)
        error_log.append(error_message)

def update_ddb_records(detached_volumes):
    """
    Update DynamoDB records for detached EBS volumes.
    Args:
        detached_volumes (list): List of detached volume dictionaries.
    """
    scan_response = scan_ebs_volume_ddb_records(EBS_VOLUME_DDB_TABLE)

    for table_item in scan_response['Items']:
        detached_volume_entry = get_detached_volume(detached_volumes, table_item['VolumeId']['S'])

        # If Table Item is in detached volumes - Already accounted for in Table: Remove from detached_volumes list (don't need to add it to table - already tagged)
        if detached_volume_entry is not None:

            # Check if EBS volume has any configuration changes
            if table_item['VolumeType']['S'] != detached_volume_entry['VolumeType'] \
                or table_item['VolumeSize']['N'] != str(detached_volume_entry['VolumeSize']) \
                or table_item['VolumeIops']['N'] != str(detached_volume_entry['VolumeIops']) \
                or table_item['VolumeThroughput']['N'] != str(detached_volume_entry['VolumeThroughput']) \
                or f"{float(table_item['MonthlyCost']['N']):.2f}" != str(detached_volume_entry['MonthlyCost']):
                print('updating:', table_item['VolumeId']['S'])
                update_ebs_volume_ddb_record(detached_volume_entry)

            # Check if EBS volume has deletion tag and if it is accurate
            deletion_tag_value = check_ebs_volume_for_deletion_tag(detached_volume_entry)
            if deletion_tag_value is None or deletion_tag_value != table_item['DeletionDate']['S']:
                print('Tagging: ', table_item['VolumeId']['S'], " in account:", table_item['AccountName']['S'], "with ddb deletion date of ", table_item['DeletionDate']['S'])
                tag_ebs_volume(detached_volume_entry['VolumeId'], \
                    detached_volume_entry['AccountId'], \
                    detached_volume_entry['Region'], \
                    detached_volume_entry['Environment'], \
                    table_item['DeletionDate']['S'])

            # Since volume is already accounted for and updated, delete from new detached volumes list
            detached_volumes = [obj for obj in detached_volumes if obj.get('VolumeId') != table_item['VolumeId']['S']]
        else:
            try:
                print(f"Item in DDB table not in current detached volumes list: {table_item['VolumeId']['S']}, needs to be removed from DDB table")

                ebs_volume_search = get_volumes_by_id(table_item['VolumeId']['S'], table_item['AccountId']['S'], table_item['AccountName']['S'], table_item['ResourceRegion']['S'])
                if ebs_volume_search != []:
                    if (check_ebs_volume_for_deletion_tag(ebs_volume_search[0]) is not None):
                        untag_volume(table_item['VolumeId']['S'], table_item['AccountId']['S'], table_item['ResourceRegion']['S'])
                    remove_ebs_volume_ddb_record(table_item['VolumeId']['S'])
                else:
                    remove_ebs_volume_ddb_record(table_item['VolumeId']['S'])

            except ClientError as e:
                error_message = f"Error in DynamoDB delete_item ({table_item['VolumeId']['S']}): {str(e)}"
                print(error_message)
                error_log.append(error_message)

    # Check if there volumes in detatched volumes list that aren't in table 
    # Indicates they are newly detached
    for new_detached_volume in detached_volumes:
        create_ebs_volume_ddb_record(new_detached_volume)
        tag_ebs_volume(new_detached_volume['VolumeId'], new_detached_volume['AccountId'], \
            new_detached_volume['Region'], new_detached_volume['Environment'], "")

    return

def check_string_in_array_of_objects(array, string_to_check):
    """
    Check if a string is present in an array of objects.
    Args:
        array (list): A list of objects to search.
        string_to_check (str): The string to check for.
    Returns:
        bool: True if the string is found, False otherwise.
    """
    for obj in array:
        if obj['VolumeId'] == string_to_check:
            return True
    return False

def check_ebs_volume_for_deletion_tag(ebs_volume_obj):
    """Check if an EBS volume has a deletion tag.
    Args:
        ebs_volume_obj (dict): The EBS volume object to check.
    Returns:
        str: The deletion date if found, None otherwise.
    """
    tags = ebs_volume_obj.get('Tags', [])
    for tag in tags:
        if tag['Key'] == 'identified_for_deletion':
            return tag['Value']

    return False

def tag_ebs_volume(volume_id, account_id, region_name, env, ddb_deletion_date):
    """
    Tag an EBS volume for deletion.
    Args:
        volume_id (str): The ID of the EBS volume to tag.
        account_id (str): The ID of the AWS account.
        region_name (str): The name of the AWS region.
        env (str): The environment (e.g., 'prod', 'dev').
        ddb_deletion_date (str): The deletion date from DynamoDB, if available.
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
                volume_id,
            ],
            Tags=[
                {
                    'Key': 'identified_for_deletion',
                    'Value': deletion_date,
                },
            ],
        )
    except ClientError as e:
        error_message = f"Error in tagging EBS Volume ({volume_id}): {str(e)}"
        print(error_message)
        error_log.append(error_message)

    return

def get_volumes_by_id(volume_id, account_id, account_name, region):
    """
    Get EBS Volume by ID across accounts.
    Args:
        volume_id (str): The ID of the EBS volume.
        account_id (str): The ID of the AWS account.
        account_name (str): The name of the AWS account.
        region (str): The name of the AWS region.
    Returns:
        list: A list of EBS volume objects.
    """
    detached_volume_list_output = []

    try:
        access_key, secret_access_key, session_token = assume_new_account_role(account_id)
        ec2_client = get_multi_account_ec2_client(access_key, secret_access_key, session_token, region)

        # Get initial detached volumes list
        response = ec2_client.describe_volumes(VolumeIds=[volume_id])
        detached_volume_list_output = response['Volumes']

    except ClientError as e:
        error_message = f"Error in finding EBS Volume ({volume_id} in {account_id}, {account_name} - {region}): {str(e)}"
        print(error_message)
        error_log.append(error_message)

    return detached_volume_list_output

def untag_volume(volume_id, account_id, region):
    """
    Untag an EBS volume across accounts.
    Args:
        volume_id (str): The ID of the EBS volume to untag.
        account_id (str): The ID of the AWS account.
        region (str): The name of the AWS region.
    """
    try:
        access_key, secret_access_key, session_token = assume_new_account_role(account_id)
        ec2_client = get_multi_account_ec2_client(access_key, secret_access_key, session_token, region)
        ec2_client.delete_tags(
            Resources=[
                volume_id,
            ],
            Tags=[
                {
                    'Key': 'identified_for_deletion'
                },
            ]
        )
    except ClientError as e:
        error_message = f"Error in removing tags from EBS Volume ({volume_id}): {str(e)}"
        print(error_message)
        error_log.append(error_message)

    return

def calculate_monthly_cost(volumes):
    """Calculate the monthly cost of EBS volumes.

    Args:
        volumes (list): A list of EBS volume objects.

    Returns:
        float: The total monthly cost of the EBS volumes.
    """
    total_cost = 0.0

    for volume in volumes:
        # Get the price per GB-month for the volume type and region
        region_pricing = EBS_PRICING.get(volume['Region'], {})
        if volume['VolumeType'] not in region_pricing:
            print(f"Error: Unsupported volume type : {volume['VolumeType']} for region: {volume['Region']} in volume ID: {volume['VolumeId']}")
            continue

        # Get the price per GB-month for the volume type and region
        price_per_gb_month = region_pricing[volume['VolumeType']].get('price_per_gb_month', 0.0)
        volume_cost = volume['VolumeSize'] * price_per_gb_month
        total_cost += volume_cost

        # Calculate IOPS cost for gp3 volumes
        if volume['VolumeType'] == 'gp3':
            iops_price_per_unit = region_pricing.get(volume['VolumeType'], {}).get('iops_price_per_unit', 0.0)
            throughput_price_per_unit = region_pricing.get(volume['VolumeType'], {}).get('throughput_per_unit', 0.0)
            if volume.get('VolumeIops', 0) > 3000:
                iops_cost = (volume.get('VolumeIops', 0) - 3000) * iops_price_per_unit
                volume_cost += iops_cost
                total_cost += iops_cost
            if volume.get('VolumeThroughput', 125) > 125:
                throughput_cost = (volume.get('VolumeThroughput', 125) - 125) * throughput_price_per_unit
                volume_cost += throughput_cost
                total_cost += throughput_cost

        if volume['VolumeType'] == 'io1':
            iops_price_per_unit = region_pricing.get(volume['VolumeType'], {}).get('iops_price_per_unit', 0.0)
            iops_cost = (volume.get('VolumeIops', 0)) * iops_price_per_unit
            volume_cost += iops_cost
            total_cost += iops_cost

        if volume['VolumeType'] == 'io2':
            if volume.get('VolumeIops', 0) <= 32000:
                iops_price_per_unit = region_pricing.get(volume['VolumeType'], {}).get('iops_price_per_unit_under_32000', 0.0)
            elif volume.get('VolumeIops', 0) > 64000:
                iops_price_per_unit = region_pricing.get(volume['VolumeType'], {}).get('iops_price_per_unit_under_64000', 0.0)
            else:
                iops_price_per_unit = region_pricing.get(volume['VolumeType'], {}).get('iops_price_per_unit_over_64000', 0.0)

            iops_cost = (volume.get('VolumeIops', 0)) * iops_price_per_unit
            volume_cost += iops_cost
            total_cost += iops_cost

        volume['MonthlyCost'] = f"{volume_cost:.2f}"

    return total_cost

def publish_sns_topic(subject_message, sns_input):
    """
    Publish a message to an SNS topic.
    Args:
        subject_message (str): The subject line for the SNS message.
        sns_input (dict): The input message to be published to the SNS topic.
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
        print("Encountered Unknown Error when publishing to SNS Topic", SNSTOPICARN, " in EBS Volume Inventory Lambda: ", e)
        raise
    return

def lambda_handler(event, context):
    """
    Handles the Lambda function execution.
    Args:
        event (dict): The event data passed to the Lambda function.
        context (LambdaContext): The context object providing information about the invocation.
    Returns:
        dict: The response from the Lambda function.
    """
    print("Event: ", event, "Context: ", context)
    detached_volumes = []
    account_list = get_active_accounts()
    for account in account_list:
        if account['AccountStatus']['S'] == "ACTIVE":
            access_key, secret_access_key, session_token = assume_new_account_role(account['AccountId']['S'])
            detached_volumes.extend(get_detached_volumes(account['AccountId']['S'], account['AccountName']['S'], account['Environment']['S'], ACTIVE_REGIONS, access_key, secret_access_key, session_token))

    total_monthly_cost = calculate_monthly_cost(detached_volumes)
    print(f"Total Monthly Cost for Unattached EBS Volumes: ${total_monthly_cost:.2f}")
    update_ddb_records(detached_volumes)

    if error_log:
        message = ""
        for error in error_log:
            message += error + ",\n"
        print(message)
        publish_sns_topic('EBS Volume Inventory Issues', message)

    return {
        'statusCode': 200,
        'body': 'EBS Inventory Completed Successfully'
    }
