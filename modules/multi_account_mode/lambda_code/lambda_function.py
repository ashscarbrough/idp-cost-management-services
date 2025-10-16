"""
This function pulls all AWS accounts in the organization and updates a
DynamoDB table with the account information.
It assumes a role in the management account to get the list of accounts and their details.
It also handles errors and sends notifications via SNS if any issues occur during the process.

Returns:
    dict: A dictionary containing the status code and a message indicating the 
    result of the operation.
"""

import os
import datetime
import json
import boto3
import botocore
from botocore.exceptions import ClientError

INACTIVE_ACCOUNTS = os.environ['INACTIVE_ACCOUNTS'].split(',')
ACCOUNT_ROLE_ARN = os.environ['ACCOUNT_ROLE_ARN']
DDB_TABLE = os.environ['ACCOUNTS_DDB_TABLE']
SNSTOPICARN=os.environ['SNS_ARN']

error_log = []

def assume_new_account_role():
    """Assume a role in a new AWS account.

    Returns:
        tuple: A tuple containing the access key, secret access key, and session token.
    """
    sts_connection = boto3.client('sts')
    acct_connection = sts_connection.assume_role(
        RoleArn=ACCOUNT_ROLE_ARN,
        RoleSessionName="cross_acct_lambda"
    )

    access_key = acct_connection['Credentials']['AccessKeyId']
    secret_access_key = acct_connection['Credentials']['SecretAccessKey']
    session_token = acct_connection['Credentials']['SessionToken']

    return access_key, secret_access_key, session_token

def update_accounts_in_dynamodb(account_list) -> None:
    """Update AWS account information in DynamoDB.

    Args:
        account_list (list): A list of dictionaries containing account information.
    """
    # Put account information into DynamoDB table
    session = boto3.Session()
    dynamodb_client = session.client('dynamodb')

    try:
        for account in account_list:
            dynamodb_client.update_item(
                Key={
                    'AccountId': {
                        'S': account['AccountId'],
                    }
                },
                UpdateExpression="SET Arn = :arn, Email = :email, GlobalRegion = :globalRegion, \
                    AccountName = :accountName, AccountStatus = :status, JoinedMethod = :joinedMethod, \
                    JoinedDatetime = :joinedDatetime, Custodian = :custodian, AccountOwner = :owner, \
                    CostCenter = :costCenter, CostDepartment = :costDepartment, Environment = :environment, \
                    ParentId = :parentId, ParentType = :parentType, LastUpdated = :lastUpdated",
                ExpressionAttributeValues={
                    ':arn': {'S': account['Arn']},
                    ':email': {'S': account['Email']},
                    ':globalRegion': {'S': account['GlobalRegion']},
                    ':accountName': {'S': account['AccountName']},
                    ':status': {'S': account['AccountStatus']},
                    ':joinedMethod': {'S': account['JoinedMethod']},
                    ':joinedDatetime': {'S': account['JoinedDatetime']},
                    ':custodian': {'S': account['Custodian']},
                    ':owner': {'S': account['AccountOwner']},
                    ':costCenter': {'S': account['CostCenter']},
                    ':costDepartment': {'S': account['CostDepartment']},
                    ':environment': {'S': account['Environment']},
                    ':parentId': {'S': account['ParentId']},
                    ':parentType': {'S': account['ParentType']},
                    ':lastUpdated': {'S': account['LastUpdated']}
                },
                TableName=DDB_TABLE,
            )

    except ClientError as e:
        error_message = f"Error getting/updating account information in \DynamoDB table: {DDB_TABLE}: {str(e)}"
        error_log.append(error_message)
        print(error_message)
    return

def get_accounts(access_key, secret_access_key, session_token) -> list:
    """Retrieve a list of AWS accounts.

    Args:
        access_key (string): Access key for the assumed role session
        secret_access_key (string): Secret access key for the assumed role session
        session_token (string): Session token for the assumed role session

    Returns:
        list: A list of AWS accounts
    """
    # Establish Python SDK client for AWS Organizations
    organizations_client = boto3.client('organizations', aws_access_key_id = access_key, aws_secret_access_key = secret_access_key, aws_session_token = session_token)

    # Initialize List and Dictionary for Account info storage
    account_list = []
    account = {}

    # Get initial account list
    response = organizations_client.list_accounts(MaxResults=20)

    account_list_output = response['Accounts']

    # Loop list_accounts until all accounts are added to the account_list_output
    while 'NextToken' in response:
        response = organizations_client.list_accounts(MaxResults=20, NextToken=response['NextToken'])
        accounts = response['Accounts']
        account_list_output.extend(accounts) # Add new accounts to the account_list_output

    # Loop through account info in account_list_output create clean account list with needed info
    # Configure account info processing to add/remove info as needed
    for item in account_list_output:
        if item['Id'] in INACTIVE_ACCOUNTS:
            account_status = "TEST"
        else:
            account_status = item['Status']

        account['AccountId'] =  item['Id']
        account['Arn'] = item['Arn']
        account['Email'] = item['Email']
        account['AccountName'] = item['Name']
        account['AccountStatus'] = account_status
        account['JoinedMethod'] = item['JoinedMethod']
        account['JoinedDatetime'] = (item['JoinedTimestamp']).strftime("%Y-%m-%d %H:%M:%S")

        # Get tags for each account (Augment as needed)
        tag_response = (organizations_client.list_tags_for_resource(ResourceId=item['Id']))['Tags']
        for tag in tag_response:
            if tag['Key'] == "Custodian":
                account['Custodian'] = tag['Value']
            elif tag['Key'] == "Owner":
                account['AccountOwner'] = tag['Value']
            elif tag['Key'] == "CostCenter":
                account['CostCenter'] = tag['Value']
            elif tag['Key'] == "CostDepartment":
                account['CostDepartment'] = tag['Value']
            elif tag['Key'] == "Environment":
                account['Environment'] = (tag['Value']).lower()
            elif tag['Key'] == "Region":
                account['GlobalRegion'] = (tag['Value']).lower()

        # Get Organizations Parent/OU information for each account
        ou_parents_response = organizations_client.list_parents(ChildId=item['Id'])['Parents']
        parent = ou_parents_response[0] if len(ou_parents_response) > 0 else None
        if parent is not None:
            account['ParentId'] = parent['Id']
            account['ParentType'] = parent['Type']

        account['LastUpdated'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Update GlobalRegion based on AccountName if not set via tag
        if account.get('GlobalRegion', "") == "":
            if '-apac-' in account['AccountName'].lower():
                account['GlobalRegion'] = 'apac'
            elif '-eu-' in account['AccountName'].lower():
                account['GlobalRegion'] = 'eu'
            else:
                account['GlobalRegion'] = 'us'

        account_list.append(account.copy())

    print (json.dumps(account_list))
    print ('Number of accounts:', len(account_list))

    return account_list

def publish_sns_topic(subject_message, sns_input):
    """Publish a message to an SNS topic.

    Args:
        subject_message (string): The subject line for the SNS message
        sns_input (json_object): The input message for the SNS topic
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
    """Lambda function to handle account pull events.

    Args:
        event (dict): An event dictionary passed from the trigger source
        context (LambdaContext): The context object for the Lambda function

    Returns:
        dict: The response from the Lambda function
    """
    print("Event: ", event, "Context: ", context)
    access_key, secret_access_key, session_token = assume_new_account_role()
    account_list = get_accounts(access_key, secret_access_key, session_token)

    update_accounts_in_dynamodb(account_list)

    if error_log:
        error_log_body = ""
        for error in error_log:
            error_log_body += error + "\n"
        publish_sns_topic("Error: New Account Pull", error_log_body)

    return {
        'statusCode': 200,
        'body': 'DynamoDB account table updated with latest account information'
    }
