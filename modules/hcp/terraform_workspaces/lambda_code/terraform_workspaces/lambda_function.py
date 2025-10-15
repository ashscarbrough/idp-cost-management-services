"""
Lambda function to fetch all Terraform Cloud workspaces for a specified organization
    1. Retrieves an API token from AWS Secrets Manager.
    2. Uses the token to fetch all Terraform Cloud workspaces for a specified organization.
    3. Stores or updates the workspace information in a DynamoDB table.
"""
import os
import base64
import json
import requests
import boto3
from botocore.exceptions import ClientError

BASE_URL = "https://app.terraform.io/api/v2"
ORGANIZATION_ID = os.environ['HCP_ORG_ID']

def get_api_token():
    """Retrieve the API token from AWS Secrets Manager.

    Raises:
        e: Exception raised if there is an error retrieving the secret.

    Returns:
        str: The API token for Terraform Cloud.
    """
    secret_name = os.environ['SECRET_NAME']
    region_name = os.environ['SECRET_REGION']

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        # Retrieve the secret value
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)

        # Check if the secret value is a string (JSON format)
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            secret_dict = json.loads(secret)  # Parse the JSON string to a dictionary
            token = secret_dict.get('api_token')  # Extract the value of 'api_token'
        else:
            # Handle binary secret (unlikely in your case)
            secret = get_secret_value_response['SecretBinary']
            # You can handle binary data if needed (e.g., base64 decoding)
            # For now, assume it's base64 encoded and decode it
            token = base64.b64decode(secret).decode('utf-8')

    except ClientError as e:
        # Handle any errors (e.g., permissions issue)
        print(f"Error retrieving secret: {e}")
        raise e

    return token


def get_all_workspaces(api_token):
    """Fetch all workspaces from Terraform Cloud API.

    Returns:
        dict: A dictionary containing all workspace information.
    """

    # Headers for authentication
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/vnd.api+json"
    }

    all_workspaces = {}
    current_page = 1
    per_page = 50  # Default per page value, you can adjust based on API limitations
    total_pages = 1  # Initial assumption, will be updated after the first request

    while current_page <= total_pages:
        url = f"{BASE_URL}/organizations/{ORGANIZATION_ID}/workspaces?page[number]={current_page}&page[size]={per_page}"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            workspaces_data = response.json()["data"]
            # Collect all workspace IDs and names
            for item in workspaces_data:
                workspace_id = item["id"]
                workspace_name = item["attributes"].get("name") or "N/A"
                resource_count = item["attributes"].get("resource-count") or "N/A"
                last_updated = item["attributes"].get("latest-change-at") or "N/A"
                tags = item["attributes"].get("tag-names") or "N/A"
                description = item["attributes"].get("description") or "N/A"
                latest_change_at = item["attributes"].get("latest-change-at") or "N/A"
                created_at = item["attributes"].get("created-at") or "N/A"
                execution_mode = item["attributes"].get("execution-mode") or "N/A"
                vcs_repo_identifier = item["attributes"].get("vcs-repo-identifier") or "N/A"
                vcs_repo = item["attributes"].get("vcs-repo") or "N/A"
                locked = item["attributes"].get("locked") or "False"
                apply_duration_average = item["attributes"].get("apply-duration-average") or "N/A"
                working_directory= item["attributes"].get("working-directory") or "N/A"
                terraform_version= item["attributes"].get("terraform-version") or "N/A"
                project_id = item["relationships"]["project"]["data"]["id"]
                if item.get('relationships', {}).get('current-run', {}).get('data', {}):
                    current_run_id = item['relationships']['current-run']['data']['id']
                else:
                    current_run_id = "N/A"
                if item.get('relationships', {}).get('current-state-version', {}).get('data', {}):
                    current_state_version_id = item['relationships']['current-state-version']['data']['id']
                else:
                    current_state_version_id = "N/A"

                all_workspaces[workspace_id] = {
                    "name": workspace_name,
                    "resource_count": resource_count,
                    "last_updated": last_updated,
                    "tags": tags,
                    "created_at":created_at,
                    "execution_mode":execution_mode,
                    "vcs_repo":vcs_repo,    
                    "vcs_repo_identifier":vcs_repo_identifier,
                    "current_run_id": current_run_id,
                    "current_state_version_id": current_state_version_id,
                    "description": description,
                    "latest_change_at": latest_change_at,
                    "locked": locked,
                    "apply_duration_average": apply_duration_average,
                    "working_directory": working_directory,
                    "terraform_version": terraform_version,
                    "project_id": project_id
                }
            # Get pagination info from the 'meta' field
            pagination_info = response.json().get("meta", {}).get("pagination", {})
            total_pages = pagination_info.get("total-pages", 1)

            # Move to the next page
            current_page += 1
        else:
            print(f"Error fetching workspaces: {response.status_code} - {response.text}")
            break

    return all_workspaces

def create_workspace_records(workspaces_info):
    """
    Creates or updates resource records in a DynamoDB table for multiple workspaces.

    Parameters:
        workspaces_info (dict): A dictionary where keys are workspace IDs and values are
        dictionaries containing workspace details such as resource count, last updated date, 
        and tags.
    
    Returns:
        None
    """
    try:
        # Initialize a session using boto3
        primary_session = boto3.Session()
        dynamodb_client = primary_session.client('dynamodb', region_name='us-west-2')

        for workspace_id, info in workspaces_info.items():
            try:
                # Prepare the update expression
                update_expression = (
                    "SET WorkspaceName = :name, "
                    "ResourceCount = :resourceCount, "
                    "LastUpdated = :lastUpdated, "
                    "Tags = :tags, "
                    "ExecutionMode = :executionMode, "
                    "VcsRepo = :vcsRepo, "
                    "VcsRepoIdentifier = :vcsRepoIdentifier, "
                    "CurrentRunId = :currentRunId, "
                    "CurrentStateVersionId = :currentStateVersionId, "
                    "Description = :description, "
                    "LatestChangeAt = :latestChangeAt, "
                    "Locked = :locked, "
                    "ApplyDurationAverage = :applyDurationAverage, "
                    "WorkingDirectory = :workingDirectory, "
                    "TerraformVersion = :terraformVersion, "
                    "ProjectId = :projectId"
                )

                # Prepare the ExpressionAttributeValues
                expression_attribute_values = {
                    ':name': {'S': info.get('name', 'N/A')},
                    ':resourceCount': {'N': str(info.get('resource_count', '0'))},
                    ':lastUpdated': {'S': info.get('last_updated', 'N/A')},
                    ':tags': {'L': [{'S': tag} for tag in info.get('tags', [])]},
                    ':executionMode': {'S': info.get('execution_mode', 'N/A')},
                    ':vcsRepo': {'S': json.dumps(info.get('vcs_repo', 'N/A'))},
                    ':vcsRepoIdentifier': {'S': str(info.get('vcs_repo_identifier', 'N/A'))},
                    ':currentRunId': {'S': info.get('current_run_id', 'N/A')},
                    ':currentStateVersionId': {'S': info.get('current_state_version_id', 'N/A')},
                    ':description': {'S': info.get('description', 'N/A')},
                    ':latestChangeAt': {'S': info.get('latest_change_at', 'N/A')},
                    ':locked': {'S': str(info.get('locked', 'False'))},
                    ':applyDurationAverage': {'S': str(info.get('apply_duration_average', 'N/A'))},
                    ':workingDirectory': {'S': info.get('working_directory', 'N/A')},
                    ':terraformVersion': {'S': info.get('terraform_version', 'N/A')},
                    ':projectId': {'S': info.get('project_id', 'N/A')}
                }

                # Update the record in the DynamoDB table
                response = dynamodb_client.update_item(
                    Key={
                        'WorkspaceId': {
                            'S': workspace_id  # Use workspace_id as the key
                        }
                    },
                    UpdateExpression=update_expression,
                    ExpressionAttributeValues=expression_attribute_values,
                    TableName='terraform-workspace-table',
                )
                print(f"Workspace {workspace_id} updated successfully: {response}")

            except ClientError as e:
                error_message = f"Error updating workspace {workspace_id}: {str(e)}"
                print(error_message)

    except ClientError as e:
        print(f"Error in creating workspace records: {str(e)}")

def lambda_handler(event, context):
    """
    AWS Lambda handler function to fetch and store Terraform Cloud workspaces.
    """
    print("Event: ", event, "Context: ", context)
    api_token = get_api_token()
    workspaces = get_all_workspaces(api_token)
    create_workspace_records(workspaces)
