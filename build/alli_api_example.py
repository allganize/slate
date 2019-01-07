import copy
import json
import threading

import requests
import websocket


class AlliWebSocket(object):
    def __init__(self, endpoint, api_key, user_id, conversation_id):
        self.api_key = api_key
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.id = 0
        self.ws = websocket.WebSocketApp(endpoint,
                                         subprotocols=['graphql-ws'],
                                         on_open=self._on_open,
                                         on_message=self._on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close)
        self.response_callback_map = {}

    # Make web socket request id should be unique.
    def _next_id(self):
        self.id += 1
        return self.id

    def _request(self, request, callback):
        id = self._next_id()
        request = copy.deepcopy(request)
        request['id'] = id

        self.response_callback_map[id] = callback
        self.ws.send(json.dumps(request))

    def _on_open(self, ws):
        # After websocket connected, Client should send "connection_init" command with api-key and user-id
        req = {
            "type": "connection_init",
            "payload": {
                "api-key": self.api_key,
                'own-user-id': self.user_id,
            }
        }

        def _connection_ok_and_keepalive(id, resp):
            # Server sent the CONNECTION ACK messages after connection established.
            if resp['type'] == "connection_ack":
                # If you receive websocket ack. you can send subscribe request.
                self._subscribe_chat()
                return
            # Server sent the KEEP ALIVE messages every 10 secs.
            elif resp['type'] == "ka":  # Keep alive
                return
            self.on_error(ws, "Unknown response " + str(resp))

        self._request(req, _connection_ok_and_keepalive)

    def _on_message(self, ws, message):
        resp = json.loads(message)
        id = resp['id']

        if id in self.response_callback_map:
            callback = self.response_callback_map[id]
            callback(id, resp)
            return

        self.on_error(ws, "Unknown response " + str(resp))

    def on_error(self, ws, error):
        print("[Error]", error)
        raise Exception(error)

    def on_close(self, ws):
        print("[CLOSED]")
        pass

    def _subscribe_chat(self):
        subscribe_chat = {
            "type": "start",
            "payload": {
                "query": """
                subscription getChats($where:ChatWhereInput!) {
                    chats(where:$where) {
                        node {
                            ... on UserChat {
                                message
                                createdAt
                            }
                            ... on AgentChat {
                                message
                                createdAt
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
                }""",
                "variables": {
                    "where": {
                        "conversationWhere": {
                            "id": self.conversation_id
                        }
                    }
                }
            }
        }

        def _receive_chat(id, response):
            data = response['payload']['data']
            if not data:
                print(response)
                return

            node = data['chats']['node']
            typename = node['__typename']
            message = node['message']
            options = None

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
            if typename == "BotChat":
                blocks = json.loads(message)['blocks']
                message = ""
                for block in blocks:
                    message += block['text']
                # If bot message have options, Options contains node.chatOptions. and You should send option number(zero based index) instead text message
                options = node['chatOptions']
            print(typename, ":", message, options)

        self._request(subscribe_chat, _receive_chat)

    def start(self):
        self.ws.run_forever()


HTTP_TIMEOUT = 10  # seconds


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
        raise Exception(f"Execut fail {r.status_code} {r.content}")

    return json.loads(r.content)



if __name__ == "__main__":
    API_KEY = "EEMQRUUFMU3HDV08015MKCHJNM6SLIGE"
    GRAPHQL_ENDPOINT = "http://localhost:8100/user/"
    WS_ENDPOINT = "ws://localhost:8100/ws/user"
    USER_ID = "ko_pocoyo_id"

    headers = {
        'API-KEY': API_KEY,
        'OWN-USER-ID': USER_ID,
    }

    # Start Conversation
    gql = """
    mutation startConversation($v_placement:String!, $v_debug:Boolean) {
        startConversation(placement: $v_placement, debug:$v_debug) {
            conversation {
                id
            }
            debug
        }
    }
    """

    variables = {
        'v_placement': "LANDING",
        "v_debug": True
    }

    result = execute_gql(GRAPHQL_ENDPOINT, gql, variables=variables, headers=headers)
    conversation = result['data']['startConversation']['conversation']
    if not conversation:
        exit(-1)

    conversation_id = conversation['id']

    # Receive chat messages using websocket
    alli_ws = AlliWebSocket(WS_ENDPOINT, API_KEY, USER_ID, conversation_id)
    thread = threading.Thread(target=lambda: alli_ws.start())
    thread.start()

    # Send Text Message
    gql = """
    mutation sendChat($v_convId:ID!, $v_message:String) {
        sendChat(conversationId: $v_convId, message:$v_message) {
            chat {
                ... on UserChat {
                    message
                    createdAt
                }
                __typename
            }
        }
    }
    """

    variables = {
        'v_convId': conversation_id,
        "v_message": "Hello"
    }
    result = execute_gql(GRAPHQL_ENDPOINT, gql, variables=variables, headers=headers)

    # Select option
    gql = """
    mutation sendChat($v_convId:ID!, $v_selected:Int) {
        sendChat(conversationId: $v_convId, selected:$v_selected) {
            chat {
                ... on UserChat {
                    message
                    createdAt
                }
                __typename
            }
        }
    }
    """

    variables = {
        'v_convId': conversation_id,
        "v_selected": 0
    }
    result = execute_gql(GRAPHQL_ENDPOINT, gql, variables=variables, headers=headers)
