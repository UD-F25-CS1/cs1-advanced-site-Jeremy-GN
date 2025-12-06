from drafter import set_site_information, hide_debug_information, set_website_title, set_website_framed, route, Page, TextArea, LineBreak, Button, start_server, Pre
from dataclasses import dataclass
from drafter.llm import LLMMessage, LLMResponse, call_gemini
from typing import Optional



set_site_information(
    author="cjwells@udel.edu, jgn@udel.edu",
    description="Build a website using Gemini LLMs with Drafter",
    sources="Official drafter documentation",
    planning="",
    links=["https://github.com/UD-F25-CS1/cs1-advanced-site-Jeremy-GN"]
)

#set_gemini_server("https://drafter-gemini-proxy.jgn.workers.dev/")

with open("styles.css", "r") as file:
    main_screen_css: str = "<style>" + file.read() + "</style>"

hide_debug_information()
set_website_title("Your Drafter Website")
set_website_framed(False)

@dataclass
class WebsiteBuild:
    website_html: str


@dataclass
class State:
    """
    The state of our website builder application.

    :param last_website: The most recently built website
    :type last_website: WebsiteBuild | None
    :param last_description: The user's description for the last build
    :type last_description: str
    :param last_raw_response: The raw response from Gemini
    :type last_raw_response: str
    """
    last_website: Optional[WebsiteBuild]
    last_description: str
    last_raw_response: str


@route
def index(state: State) -> Page:
    """
    Main page of the website builder application.
    """
    return show_builder(state)


def parse_website_response(response_text: str) -> WebsiteBuild:
    """
    Parse the LLM response to extract HTML.
    The HTML should already contain <style> and <script> tags inside it.
    We keep the complete HTML with all styling intact.
    """
    html = ""

    # Extract HTML (which should include <style> and <script> tags)
    html_start = response_text.find("<html>")
    html_end = response_text.find("</html>")
    if html_start != -1 and html_end != -1:
        html = response_text[html_start:html_end + 7]

    return WebsiteBuild(html)


@route
def build_website(state: State, description: str) -> Page:
    """Send the website description to Gemini and build the website."""
    if not description.strip():
        return show_builder(state)

    # Create a prompt for Gemini to generate website code
    prompt = f"""Generate a complete HTML website based on this description: {description}

IMPORTANT CONSTRAINTS:
- Keep the website code COMPACT and EFFICIENT
- Use minimal CSS - only essential styling
- Avoid unnecessary HTML elements or comments
- Use inline styles where possible instead of separate <style> blocks
- Do not include external libraries or CDN links
- Keep JavaScript minimal or omit if not essential
- Use short variable names and class names

Format your response with these exact tags:
<html>
[Complete HTML structure here, including <head>, <body>, <style>, and <script> tags as needed]
</html>"""

    # Call Gemini to generate the website and handle errors/edge-cases
    messages = [LLMMessage("user", prompt)]
    try:
        result = call_gemini(messages, api_key="AIzaSyBGEULRVVYf4ZVVIjgPo1Ep3mTY19rWRyw", max_tokens=8000)
    except Exception as exc:
        # Unexpected exception when calling the API (network/proxy/library)
        error_html = (
            "<html><body><h1>Error building website</h1>"
            f"<p>Exception calling Gemini: {repr(exc)}</p>"
            "</body></html>"
        )
        new_website = WebsiteBuild(error_html)
        new_state = State(new_website, description, repr(exc))
        return show_builder(new_state)

    # If the library returned a structured error (not an LLMResponse), try
    # to recover useful text. Some proxies or streaming responses use a
    # `parts` field or return a dict-like payload; handle common shapes.
    content_text = None
    raw_response = ""
    if isinstance(result, LLMResponse):
        content_text = result.content
        raw_response = result.content
    else:
        # Try common fallbacks: dict-like with 'parts', or .message
        try:
            if isinstance(result, dict) and "parts" in result:
                # parts may be a list of text chunks
                parts = result.get("parts") or []
                assembled = []
                for p in parts:
                    if isinstance(p, dict):
                        assembled.append(p.get("text") or p.get("content") or "")
                    else:
                        assembled.append(str(p))
                content_text = "".join(assembled)
            elif hasattr(result, "message") or hasattr(result, "__dict__"):
                # library-style error object with a message (use getattr fallback)
                err_msg = getattr(result, "message", str(result))
                error_html = (
                    "<html><body><h1>Error building website</h1>"
                    f"<p>{err_msg}</p>"
                    "</body></html>"
                )
                new_website = WebsiteBuild(error_html)
                raw_response = err_msg
                new_state = State(new_website, description, raw_response)
                return show_builder(new_state)
            else:
                # Last resort: stringify the object
                content_text = str(result)
                raw_response = str(result)
        except KeyError as ke:
            # This often surfaces as "'parts'" in error messages
            error_html = (
                "<html><body><h1>Error building website</h1>"
                f"<p>KeyError accessing response parts: {repr(ke)}</p>"
                "</body></html>"
            )
            new_website = WebsiteBuild(error_html)
            new_state = State(new_website, description, repr(ke))
            return show_builder(new_state)

    # If we have some text from the LLM, parse it into html/css/js
    if content_text:
        new_website = parse_website_response(content_text)
        new_state = State(new_website, description, raw_response)
    else:
        # No usable content returned
        error_html = (
            "<html><body><h1>No content returned</h1>"
            "<p>The LLM returned no usable content.</p>"
            "</body></html>"
        )
        new_website = WebsiteBuild(error_html)
        new_state = State(new_website, description, raw_response)

    return show_builder(new_state)


def show_builder(state: State) -> Page:
    """Display the website builder interface."""
    content = [
        main_screen_css,
        "Describe the website you want to build:",
        TextArea("description", "", rows=5, cols=50),
        LineBreak(),
        Button("Build Website", build_website), # type: ignore
        Button("Debug", debug_view), # type: ignore
    ]

    # Show the last built website if it exists
    if state.last_website is not None:
        content.extend([
            "---",
            "Your Built Website:",
            state.last_website.website_html,
            LineBreak(),
            Button("Build Another", index), # type: ignore
        ])

    return Page(state, content)


@route
def debug_view(state: State) -> Page:
    """Display debug information: raw response and state."""
    # Escape HTML tags by replacing <> with ()
    raw_response = state.last_raw_response or "(no response yet)"
    raw_response_escaped = raw_response.replace("<", "(").replace(">", ")")
    
    website_html = state.last_website.website_html if state.last_website else "(no website)"
    website_html_escaped = website_html.replace("<", "(").replace(">", ")")
    
    content = [
        "Debug Information",
        "---",
        "Last Description:",
        state.last_description if state.last_description else "(none)",
        "---",
        "Raw Gemini Response:",
        Pre(raw_response_escaped),
        "---",
        "Website HTML:",
        Pre(website_html_escaped),
        "---",
        Button("Back", index), # type: ignore
    ]
    return Page(state, content)


start_server(State(None, "", ""))
