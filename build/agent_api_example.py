import json

import requests

HTTP_TIMEOUT = 10


# Please see https://graphql.org/learn/serving-over-http/
def execute_gql(endpoint, gql, operation_name=None, variables=None, headers=None):
    data = {
        "query": gql,
    }
    if operation_name:
        data['operationName'] = operation_name
    if variables:
        data['variables'] = variables

    if not headers:
        headers = {}

    headers['Content-Type'] = 'application/json'

    r = requests.post(endpoint,
                      data=json.dumps(data),
                      headers=headers,
                      timeout=HTTP_TIMEOUT)

    if not r.ok:
        raise Exception(f"Execute fail {r.status_code} {r.content}")

    ret = json.loads(r.content)
    if 'data' not in ret or not ret['data']:
        raise Exception("Execute fail. ret=", str(ret))
    return ret['data']


# AgentChat and UserChat .message is plain text.
# BotChat.message is not simple text, It has json format. # All messages are in blocks.text. You can ignore entityRanges and entityMap.
# BotChat.message example
# {
#     "blocks": [
#         {
#             "text": "Hi Pocoyo Good to see you back.",
#             "entityRanges": [...]
#         }
#     ],
#     "entityMap": {...}
# }
def get_plain_text(chat):
    typename = chat['__typename']
    message = chat['message']
    options = None
    if typename == "BotChat":
        blocks = json.loads(message)['blocks']
        message = ""
        for block in blocks:
            message += block['text']
        # If bot message have options, Options contains node.chatOptions. and You should send option number(zero based index) instead text message
        options = chat['chatOptions']

    return typename, message, options


if __name__ == "__main__":
    GRAPHQL_ENDPOINT = "https://backend.alli.ai/d/graphql/"

    # signin
    gql = """
    mutation signin($email:String!, $passwd:String!) {
        login(email:$email, password:$passwd) {
            token
        }
    }
    """
    variables = {
        "email": "",
        "passwd": ""
    }

    token = execute_gql(GRAPHQL_ENDPOINT, gql, variables=variables)['login']['token']
    auth_headers = {
        'AUTHORIZATION': token

    }

    # Get campaigns
    # Please see graphql relay spec. https://facebook.github.io/relay/graphql/connections.htm
    gql = """
    query getCampaigns($filter:CampaignFilter) {
        campaigns(filter:$filter) {
            edges {
                node {
                    id
                    name
                }
            }
        }
    }
    """
    # You can add CampaignFilter or order. They are not mandatory.
    variables = {
    }

    campaigns = execute_gql(GRAPHQL_ENDPOINT, gql, variables=variables, headers=auth_headers)['campaigns']['edges']
    for campaign in campaigns:
        id = campaign['node']['id']
        name = campaign['node']['name']
        print(f"{id}, {name}")

    # Get conversations
    # Please see graphql relay spec. https://facebook.github.io/relay/graphql/connections.htm
    gql = """
    query getConversations($filter:ConversationFilterInput, $limit:Int) {
        conversations(filter:$filter, first:$limit) {
            edges {
                node {
                    id
                    user {
                        ownUserId
                    }
                    chats {
                        edges {
                            node {
                                ... on UserChat {
                                    message
                                }
                                ... on AgentChat {
                                    message
                                    agent {
                                        name
                                    }
                                }
                                ... on BotChat {
                                    message
                                    createdAt
                                    chatOptions
                                }
                                __typename
                                }
                        }
                    }
                }
            }
        }
    }
    """
    # You can add ConversationFilterInput or ConversationOrder. They are not mandatory.
    variables = {
        "limit": 10  # Please add limit. see
    }
    conversations = execute_gql(GRAPHQL_ENDPOINT, gql,
                                variables=variables,
                                headers=auth_headers)['conversations']['edges']
    for conv in conversations:
        conv = conv['node']
        id = conv['id']
        user = conv['user']['ownUserId']
        print(f"ConvId({id}), User({user})")
        for chat in conv['chats']['edges']:
            typename, message, options = get_plain_text(chat['node'])
            print(f"\t{typename} : {message}, {options}")

    # Get users and user variables
    # Please see graphql relay spec. https://facebook.github.io/relay/graphql/connections.htm
    gql = """
    query getUsers($filter:UserFilter, $limit:Int) {
        users(filter:$filter, first:$limit) {
            edges {
                node {
                    ownUserId
                    name
                    online
                    variables {
                        edges {
                            node {
                                id
                                name
                            }
                            value
                            readOnly
                        }
                    }
                }
            }
        }
    }
    """
    # You can add UserFilter.
    variables = {
        "limit": 10  # Please add limit. see
    }
    users = execute_gql(GRAPHQL_ENDPOINT, gql,
                        variables=variables,
                        headers=auth_headers)['users']['edges']
    for user in users:
        user = user['node']
        id = user['ownUserId']
        name = user['name']
        print(f"Id({id}), Name({name})")
