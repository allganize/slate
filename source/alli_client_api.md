# Alli API Document


## Make campaign
-   You should see [Alli onboarding document](https://docs.google.com/document/d/1mfgtknMbnzDL6sKBKDOtWC0cnHwX59NT5nqWISqQZCE/edit#heading=h.ubhpu5uvlrg1).

## Check your API Key
- You can find your API key by selecting “Settings” from the left navigation:  
![](https://lh5.googleusercontent.com/oMS8pHElzfdZF_mRKTYJIFXdrnpPtsRaxVWedewbZtwyaHXt1SobBjMRArV8bb2IcyUv5WVzuGViFSw80G41PEyldmPUBdgzIISW_QEU4gq__CA1n52ccIigQhyIouhyQ2siqs1_)

## Tools & Library
GraphQL is implemented over standard HTTP and websocket. So you can choose any http, websocket library like python requests.

- A graphical interative in-brower GraphQL IDE : [https://github.com/graphql/graphiql  
](https://github.com/graphql/graphiql)
-   Python Library : [https://github.com/graphql-python/gql](https://github.com/graphql-python/gql)
-   Java Library : [https://github.com/apollographql/apollo-android](https://github.com/apollographql/apollo-android)
-   Node Library : [https://github.com/apollographql/apollo-client](https://github.com/apollographql/apollo-client)
-   Python websocket library : [https://pypi.org/project/websocket-client/](https://pypi.org/project/websocket-client/)

## Endpoints
-   GRAPHQL_ENDPOINT: [https://backend.alli.ai/d/user/](https://backend.alli.ai/d/user/)
- WEBSOCKET_ENDPOINT: [wss://backend.alli.ai/d/ws/user](wss://backend.alli.ai/d/ws/user)

## Client Chat API with python example
### Full example
- Please see example https://github.com/allganize/documents/blob/master/alli_api/alli_api_example.py

### Start conversation
- https://github.com/allganize/documents/blob/master/alli_api/alli_api_example.py#L195-L217
- You can start conversation using startConversation mutation. 

**Arguments**
- placement: String!, placement or url
- debug: Boolean, If set to true, return debug fields. It contains debug info

**Fields**
- conversation: Conversation, If has matched campaign, returns new conversation. If not, returns null.
- debug: JSONString, If turn on debug argument, returns debug information

**Example**

```
# Start Conversation  
gql = """  
mutation startConversation($v_placement:String!, $v_debug:Boolean) {  
  startConversation(placement: $v_placement, debug:$v_debug) { 
    conversation { 
      id 
    } debug 
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
```
### Receive chat messages over web socket
https://github.com/allganize/documents/blob/master/alli_api/alli_api_example.py#L9-L151

**Connect websocket**
```
self.ws = websocket.WebSocketApp(endpoint,  
                                 subprotocols=['graphql-ws'],  
                                 on_open=self._on_open,  
                                 on_message=self._on_message,  
                                 on_error=self.on_error,  
                                 on_close=self.on_close)
```

**Send connection_init with auth info**
```
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
``` 
**Subscribe chat**
```
subscribe_chat = {  
    "type": "start",  
    "payload": {  
        "query": """  
        subscription getChats($where:ChatWhereInput!) {       
          chats(where:$where) { 
            node { 
              ... on UserChat { 
                message createdAt 
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
...
self._request(subscribe_chat, _receive_chat)
```
### Send chat
```
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
```
