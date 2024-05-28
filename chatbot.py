from transformers import AutoTokenizer, TFAutoModelForSequenceClassification
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.llms import Ollama
import streamlit as st
import tensorflow as tf

# App title
st.set_page_config(page_title="🕵️‍♀️ ScamDetect")

# Set up the Streamlit framework
st.title('🕵️‍♀️ ScamDetect')
st.caption("🕸️ A Scam Detection chatbot powered by LLAMA3")

# Store LLM generated responses in chat rooms
if "rooms" not in st.session_state:
    st.session_state.rooms = [
        [{"role": "assistant", "content": "Please input your suspicious text."}]
    ]

if "current_room" not in st.session_state:
    st.session_state.current_room = 0

current_room_messages = st.session_state.rooms[st.session_state.current_room]
# Display or clear chat messages
for message in current_room_messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# User-provided input
if user_input := st.chat_input():
    current_room_messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

# Initialize the Text Classification Model
tokenizer = AutoTokenizer.from_pretrained("pippinnie/scam_text_classifier")
model = TFAutoModelForSequenceClassification.from_pretrained("pippinnie/scam_text_classifier")

# Initialize the Ollama model
llm = Ollama(model="llama3")

# Define a prompt template for the chatbot
prompt_format = '''[<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are a scam text expert who explains things in a clear and concise manner that is easy to understand.
The first input from the user is a text they are suspicious of being a scam and is sent for a text classifier who provides a label, either scam or safe and the likelihood.
You love teaching the user to understand why a text is likely or unlikely to be a scam, and teach them how to identify such texts.

Analyze the provided text based on the label and the likelihood, and present your analysis in the following format:

| Label | Possibility |
|---|---|
| {label} | {likelihood:.1%} |

Explanation

Answer any follow-up questions the user may have based on the following chat history.
If they don't have any questions, remind them to open a new chat room for another suspicious text.
{chat_history}
<|eot_id|><|start_header_id|>user<|end_header_id|>
{input}<|eot_id|><|start_header_id|>assistant<|end_header_id|>'''

prompt = ChatPromptTemplate.from_template(prompt_format)

# Create a chain that combines the prompt and the Ollama model
chain = prompt|llm

def clasify_scam(text):
    inputs = tokenizer(text, return_tensors="tf")
    logits = model(**inputs).logits

    predicted_class_id = int(tf.math.argmax(logits, axis=-1)[0])
    label = model.config.id2label[predicted_class_id]

    # Apply softmax to get probabilities
    probabilities = tf.nn.softmax(logits, axis=-1)

    # Get the probability of the label
    likelihood = probabilities[0][predicted_class_id].numpy()

    return (label, likelihood)

def create_chat_history():
    chat_history = []
    for message in current_room_messages:
        if message["role"] == "assistant":
            chat_history.append(AIMessage(content=message["content"]))
        else:
            chat_history.append(HumanMessage(content=message["content"]))
    return chat_history

def clear_chat_history():
    st.session_state.rooms[st.session_state.current_room] = [{"role": "assistant", "content": "Please input your suspicious text."}]
st.sidebar.button('🗑️ Clear Current Room', on_click=clear_chat_history)

def new_chat():
    st.session_state.rooms.append([{"role": "assistant", "content": "Please input your suspicious text."}])
    st.session_state.current_room = len(st.session_state.rooms) - 1
st.sidebar.button('➕ New Chat', on_click=new_chat)

st.sidebar.header("Chat Rooms")
for i, room in enumerate(st.session_state.rooms):
    room_icon = ''
    if (st.session_state.current_room == i):
        room_icon = ' 📌'
    if st.sidebar.button(f'Room {i+1}{room_icon}'):
        st.session_state.current_room = i

def get_initial_user_input():
    for message in current_room_messages:
        if message["role"] == "user":
            return message["content"]
    return ""

# Generate a new response if last message is not from assistant
if current_room_messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Get the initial user input
            initial_user_input = get_initial_user_input()
            # Get the scam likelihood based on the initial user input
            label, likelihood = clasify_scam(initial_user_input)

            print(label, likelihood)

            # Get user prompt from the latest user message
            user_prompt = current_room_messages[-1]["content"]
            # Invoke the chain with the user prompt
            response = chain.invoke({
                "chat_history": create_chat_history(),
                "label": label,
                "likelihood": likelihood,
                "input": user_prompt})
            st.write(response)
            # Update chat history
            message = {"role": "assistant", "content": response}
            current_room_messages.append(message)

    print(current_room_messages)
