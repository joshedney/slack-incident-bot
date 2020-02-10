import boto3
import json
import time
from django.conf import settings

# Create required AWS client
lambda_client = boto3.client(
    'lambda',
    aws_access_key_id=settings.ACCESS_KEY,
    aws_secret_access_key=settings.SECRET_KEY,
    region_name=settings.REGION_NAME
)

ssm_client = boto3.client(
    'ssm',
    aws_access_key_id=settings.ACCESS_KEY,
    aws_secret_access_key=settings.SECRET_KEY,
    region_name=settings.REGION_NAME
)

ec2_client = boto3.client(
    'ec2',
    aws_access_key_id=settings.ACCESS_KEY,
    aws_secret_access_key=settings.SECRET_KEY,
    region_name=settings.REGION_NAME
)

# Invoke the scale up lambda function
def invoke_lambda_scaleup(payload, user):
    response = lambda_client.invoke(
        FunctionName='AutoscalingStack-AutoscalingFnDC9F6EC2-LYHHUSBLLKIF',
        InvocationType='RequestResponse',
        LogType='Tail',
        Payload=json.dumps({'type': payload})
    )

    # Set the right emoji depening on the payload
    if "normal" in payload:
        emoji = ":hourglass:"
    elif "large" in payload:
        emoji = ":hourglass_flowing_sand:"
    elif "emergency" in payload:
        emoji = ":fire_engine:"

    if response['StatusCode'] == 200:
        message = f"{emoji} {user} has initiateded the *{payload}* autoscaling policy"
    else:
        message = f":sadpanda: There was an error initiating the {payload} scaling policy"

    return message


# Get the ID of a give EC2 role
def get_instance_id(role):
    role_filter = [{
        'Name': 'tag:role',
        'Values': [
            role
        ]
    }]

    response = ec2_client.describe_instances(Filters=role_filter)

    instance_id = response['Reservations'][0]['Instances'][0]['InstanceId']

    return instance_id


# Block deploys via AWS SSM
def block_deploys(user):
    response = ssm_client.send_command(
        Targets=[
            {
                'Key': 'tag:role',
                'Values': [
                    'debug',
                ]
            },
        ],
        DocumentName='BLU-BlockDeploys',
        MaxErrors='3',
        Comment='Block Deploys from Incident Bot'
    )

    command_id = response['Command']['CommandId']

    time.sleep(20)

    response = ssm_client.get_command_invocation(
        CommandId=command_id,
        InstanceId=get_instance_id("debug")
    )

    status_code = response['ResponseCode']

    if status_code == -1:
        message = f"There was an error blocking deploys.\n {response}"
    elif status_code == 0:
        message = f"Deploys have been blocked across all clients by <@{user}>"
    else:
        message = f"There was an unknown error blocking deploys.\n {response}"

    return message
