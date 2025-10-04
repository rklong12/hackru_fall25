import json
import requests
import streamlit as st
import snowflake.connector
import sseclient
import os
from dotenv import load_dotenv

load_dotenv()

ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
USER = os.getenv("SNOWFLAKE_USER")
API_KEY = os.getenv("SNOWFLAKE_API_KEY")  # your Snowflake password or API key
ROLE = os.getenv("SNOWFLAKE_ROLE")  # default role if not provided
HOST = os.getenv("SNOWFLAKE_HOST")

# API configuration 
API_ENDPOINT = "/api/v2/cortex/inference:complete"
API_TIMEOUT = 50000  # in milliseconds
MODEL_NAME = "claude-3-5-sonnet" # change me to mistral-large2, llama3.1-70b or claude-3-5-sonnet and see what happens!

# Chat assistant defaults 
icons = {"assistant": "❄️", "user": "⛷️"}

# Stremalit app title
st.set_page_config(page_title="Snowflake REST API")

default_message = [{"role": "assistant", "content": "Hi. I'm a simple chat bot that uses `"+MODEL_NAME+"` to answer questions. Ask me anything."}]


def clear_chat_history():
    st.session_state.messages = default_message


def api_call(prompt: str):

    text = ""
    sql = ""
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "content": prompt
            }
        ],
        "top_p": 0,
        "temperature": 0
    }
    
    resp = requests.post(
            url=f"https://{HOST}"+API_ENDPOINT,
            json=payload,
            headers={
                "Authorization": f'Snowflake Token="{st.session_state.CONN.rest.token}"'
            }
        ,stream=True)

    #try:
    if resp.status_code < 400:
        client = sseclient.SSEClient(resp)


        for event in client.events():

            try: 
                parsed = json.loads(event.data)

                try: 
                    if parsed['choices'][0]['delta']['type'] == 'text': 
                        text = parsed['choices'][0]['delta']['text']
                        #parsed
                        yield text

                    else: 
                        text = parsed
                        yield text


                except:
                    continue
            except:
                continue

    #except: 
    #    yield "Sorry, I've run into an error with this request! :( \n\n It's likely that my API request is malformed. You can try debugging in the `api_call()` function."

def connect_to_snowflake():
    # connection
    if 'CONN' not in st.session_state or st.session_state.CONN is None:

        try: 
            st.session_state.CONN = snowflake.connector.connect(
                user=USER,
                password=API_KEY,
                account=ACCOUNT,
                host=HOST,
                port=443,
                role=ROLE
            )  
            st.info('Snowflake Connection established!', icon="💡")    
        except:
            st.error('Connection not established. Check that you have correctly entered your Snowflake credentials!', icon="🚨")    

def main():

    st.sidebar.title("My First Chat App")

    st.sidebar.caption("Visit [CORTEX PLAYGROUND](https://app.snowflake.com/_deeplink/#/cortex/playground) for an interactive interface to test out models, and view model availability")

    st.sidebar.button('Clear chat history', on_click=clear_chat_history)
# Initialize Snowflake connection state
if "CONN" not in st.session_state:
    st.session_state.CONN = None

connect_to_snowflake()

# Initialize messages if not present
if "messages" not in st.session_state:
    st.session_state.messages = default_message

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar=icons[message["role"]]):
        st.write(message["content"])

# User input
if prompt := st.chat_input(disabled=not st.session_state.CONN):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=icons["user"]):
        st.write(prompt)

    # Generate a new response if last message is not from assistant
    if st.session_state.messages[-1]["role"] != "assistant":
        with st.chat_message("assistant", avatar=icons["assistant"]):
            response = api_call(prompt)
            full_response = st.write_stream(response)
        message = {"role": "assistant", "content": full_response}
        st.session_state.messages.append(message)
            
   
if __name__ == "__main__":
    main()