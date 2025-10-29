#Note: This is code which I had in my Lambda function, I did not run it locally anywhere in this app. This code was integrated with AWS API Gateway and Dynamo DB, and Lambda.
#It was ran in the AWS Console.

import json
import boto3
import uuid

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Tasks')

cognito = boto3.client('cognito-idp')
USER_POOL_ID = 'us-east-1_SE2OKlq4a'

def lambda_handler(event, context):
    http_method = event.get('httpMethod', '')
    user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub', 'test-user3')
    
    # Handle OPTIONS preflight requests
    if http_method == 'OPTIONS':
        return response(200, {'message': 'CORS preflight'})
    path = event.get('path', '')
    if http_method == 'POST' and path.endswith('/check-user'):
        return check_user_exists(event)

    if http_method == 'GET':
        return get_tasks(user_id)
    elif http_method == 'POST':
        return create_task(event, user_id)
    elif http_method == 'PUT':
        return update_task(event, user_id)
    elif http_method == 'DELETE':
        return delete_task(event, user_id)
    else:
        return response(400, {'error': f'Invalid method: {http_method}'})

def get_tasks(user_id):
    try:
        result = table.query(
            KeyConditionExpression='userID = :uid',
            ExpressionAttributeValues={':uid': user_id}
        )
        tasks = result.get('Items', [])
        return response(200, {'tasks': tasks})
    except Exception as e:
        return response(500, {'error': str(e)})

def create_task(event, user_id):
    try:
        body = json.loads(event['body'])
        task_id = str(uuid.uuid4())
        
        item = {
            'userID': user_id,
            'taskID': task_id,
            'text': body.get('text', ''),
            'done': body.get('done', False),
            'dueDate': body.get('dueDate', '')
        }
        
        table.put_item(Item=item)
        return response(201, {'message': 'Task created', 'task': item})
    except Exception as e:
        return response(500, {'error': str(e)})

def update_task(event, user_id):
    try:
        task_id = event['pathParameters']['id']
        body = json.loads(event['body'])
        
        table.update_item(
            Key={'userID': user_id, 'taskID': task_id},
            UpdateExpression='SET #text = :text, done = :done, dueDate = :date',
            ExpressionAttributeNames={'#text': 'text'},
            ExpressionAttributeValues={
                ':text': body.get('text'),
                ':done': body.get('done'),
                ':date': body.get('dueDate', '')
            }
        )
        return response(200, {'message': 'Task updated'})
    except Exception as e:
        return response(500, {'error': str(e)})

def delete_task(event, user_id):
    try:
        path_params = event.get('pathParameters', {})
        task_id = path_params.get('id') if path_params else None
        
        if not task_id:
            return response(400, {'error': 'Task ID is required'})
        
        table.delete_item(
            Key={'userID': user_id, 'taskID': task_id}
        )
        return response(200, {'message': 'Task deleted successfully'})
    except Exception as e:
        return response(500, {'error': str(e)})

def response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
        'body': json.dumps(body)
    }

def check_user_exists(event):
    try:
        body = json.loads(event.get('body', '{}'))
        username = body.get('username')

        if not username:
            return response(400, {'error': 'Username is required'})

        try:
            cognito.admin_get_user(
                UserPoolId=USER_POOL_ID,
                Username=username
            )
            exists = True
        except cognito.exceptions.UserNotFoundException:
            exists = False
        except Exception as e:
            print("Error checking user:", e)
            return response(500, {'error': str(e)})

        return response(200, {'exists': exists})

    except Exception as e:
        print("Unexpected error:", e)
        return response(500, {'error': str(e)})