from drafter import set_site_information, hide_debug_information, set_website_title, set_website_framed, route, Page, TextArea, LineBreak, Button, start_server
from dataclasses import dataclass
from drafter.llm import LLMMessage, LLMResponse, call_gemini, set_gemini_server



set_site_information(
    author="testing!!",
    description="A brief description of what your website does",
    sources="List any help resources or sources you used",
    planning="your_planning_document.pdf",
    links=["https://github.com/your-username/your-repo"]
)

set_gemini_server("https://drafter-gemini-proxy.jgn.workers.dev/")


hide_debug_information()
set_website_title("Your Drafter Website")
set_website_framed(False)


@dataclass
class State:
    """
    The state of our chatbot application.

    :param conversation: List of messages in the conversation
    :type conversation: List[LLMMessage]
    """
    conversation: list[LLMMessage]


@route
def index(state: State) -> Page:
    """
    Main page of the chatbot application.
    Shows API key setup if not configured, otherwise shows the chat interface.
    """
    return show_chat(state)


def show_chat(state: State) -> Page:
    """Display the chat interface with conversation history."""
    content = [
        "Chatbot using Gemini",
        "---"
    ]

    # Show conversation history
    if state.conversation:
        for msg in state.conversation:
            if msg.role == "user":
                content.append(f"You: {msg.content}")
            elif msg.role == "assistant":
                content.append(f"Bot: {msg.content}")
        content.append("---")

    # Input for new message
    content.extend([
        "Your message:",
        TextArea("user_message", "", rows=3, cols=50),
        LineBreak(),
        Button("Send", send_message), # type: ignore
        Button("Clear Conversation", clear_conversation), # type: ignore
    ])

    return Page(state, content)


@route
def send_message(state: State, user_message: str) -> Page:
    """Send a message to the LLM and get a response."""
    if not user_message.strip():
        return show_chat(state)

    # Add user message to conversation
    user_msg = LLMMessage("user", user_message)
    state.conversation.append(user_msg)

    result = call_gemini(state.conversation)

    # Handle the result
    if isinstance(result, LLMResponse):
        # Success! Add the response to conversation
        assistant_msg = LLMMessage("assistant", result.content)
        state.conversation.append(assistant_msg)
    else:
        # Error occurred
        error_msg = LLMMessage("assistant", f"Error: {result.message}")
        state.conversation.append(error_msg)
    return show_chat(state)


@route
def clear_conversation(state: State) -> Page:
    """Clear the conversation history."""
    state.conversation = []
    return show_chat(state)


start_server(State([]))
