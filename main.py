from drafter import set_site_information, hide_debug_information, set_website_title, set_website_framed, route, Page, TextArea, LineBreak, Button, start_server
from dataclasses import dataclass
from drafter.llm import LLMMessage, LLMResponse, call_gemini, set_gemini_server
from typing import Optional
import json



set_site_information(
    author="cjwells@udel.edu, jgn@udel.edu",
    description="Build a website using Gemini LLMs with Drafter",
    sources="Official drafter documentation",
    planning="",
    links=["https://github.com/UD-F25-CS1/cs1-advanced-site-Jeremy-GN"]
)

set_gemini_server("https://drafter-gemini-proxy.jgn.workers.dev/")


hide_debug_information()
set_website_title("Your Drafter Website")
set_website_framed(False)

@dataclass
class WebsiteBuild:
    website_html: str
    website_css: str
    website_js: str


@dataclass
class State:
    """
    The state of our website builder application.

    :param last_website: The most recently built website
    :type last_website: WebsiteBuild | None
    :param last_description: The user's description for the last build
    :type last_description: str
    """
    last_website: Optional[WebsiteBuild]
    last_description: str
    # Raw LLM response (for debugging) - may be a long string
    last_raw_response: Optional[str]


@route
def index(state: State) -> Page:
    """
    Main page of the website builder application.
    """
    return show_builder(state)


def parse_website_response(response_text: str) -> WebsiteBuild:
    """
    Parse the LLM response to extract HTML, CSS, and JS.
    Assumes response is formatted with markers like:
    <html>...</html>
    <style>...</style>
    <script>...</script>
    """
    html = ""
    css = ""
    js = ""

    # Extract HTML
    html_start = response_text.find("<html>")
    html_end = response_text.find("</html>")
    if html_start != -1 and html_end != -1:
        html = response_text[html_start:html_end + 7]

    # Extract CSS (from <style> tags)
    style_start = response_text.find("<style>")
    style_end = response_text.find("</style>")
    if style_start != -1 and style_end != -1:
        css = response_text[style_start + 7:style_end]

    # Extract JavaScript (from <script> tags)
    script_start = response_text.find("<script>")
    script_end = response_text.find("</script>")
    if script_start != -1 and script_end != -1:
        js = response_text[script_start + 8:script_end]

    return WebsiteBuild(html, css, js)


@route
def build_website(state: State, description: str) -> Page:
    """Send the website description to Gemini and build the website."""
    if not description.strip():
        return show_builder(state)

    # Create a prompt for Gemini to generate website code
    prompt = f"""Generate a complete HTML website based on this description: {description}

Format your response with these exact tags:
<html>
[Complete HTML structure here, including <head> and <body>]
</html>

<style>
[CSS styling here]
</style>

<script>
[JavaScript code here if needed]
</script>"""

    # Call Gemini to generate the website and handle errors/edge-cases
    messages = [LLMMessage("user", prompt)]
    try:
        result = call_gemini(messages)
    except Exception as exc:
        # Unexpected exception when calling the API (network/proxy/library)
        error_html = (
            "<html><body><h1>Error building website</h1>"
            f"<p>Exception calling Gemini: {repr(exc)}</p>"
            "</body></html>"
        )
        new_website = WebsiteBuild(error_html, "", "")
        new_state = State(new_website, description, None)
        return show_builder(new_state)

    # If the library returned a structured error (not an LLMResponse), try
    # to recover useful text. Some proxies or streaming responses use a
    # `parts` field or return a dict-like payload; handle common shapes.
    content_text = None
    if isinstance(result, LLMResponse):
        content_text = result.content
        raw_text = result.content
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
                raw_text = json.dumps(result)
            elif hasattr(result, "message") or hasattr(result, "__dict__"):
                # library-style error object with a message (use getattr fallback)
                err_msg = getattr(result, "message", str(result))
                error_html = (
                    "<html><body><h1>Error building website</h1>"
                    f"<p>{err_msg}</p>"
                    "</body></html>"
                )
                new_website = WebsiteBuild(error_html, "", "")
                new_state = State(new_website, description, getattr(result, "message", str(result)))
                return show_builder(new_state)
            else:
                # Last resort: stringify the object
                content_text = str(result)
                raw_text = str(result)
        except KeyError as ke:
            # This often surfaces as "'parts'" in error messages
            error_html = (
                "<html><body><h1>Error building website</h1>"
                f"<p>KeyError accessing response parts: {repr(ke)}</p>"
                "</body></html>"
            )
            new_website = WebsiteBuild(error_html, "", "")
            new_state = State(new_website, description, None)
            return show_builder(new_state)

    # If we have some text from the LLM, parse it into html/css/js
    if content_text:
        new_website = parse_website_response(content_text)
        # Save raw response when available
        try:
            last_raw = raw_text  # defined above in parsing branches
        except NameError:
            last_raw = None
        new_state = State(new_website, description, last_raw)
    else:
        # No usable content returned
        error_html = (
            "<html><body><h1>No content returned</h1>"
            "<p>The LLM returned no usable content.</p>"
            "</body></html>"
        )
        new_website = WebsiteBuild(error_html, "", "")
        new_state = State(new_website, description, None)

    return show_builder(new_state)


def show_builder(state: State) -> Page:
    """Display the website builder interface."""
    content = [
        "Describe the website you want to build:",
        TextArea("description", "", rows=5, cols=50),
        LineBreak(),
        Button("Build Website", "build_website"),
        Button("Show Raw Response", "debug_view"),
    ]

    # Show the last built website if it exists
    if state.last_website is not None:
        content.extend([
            "---",
            "Your Built Website:",
            state.last_website.website_html,
            LineBreak(),
            Button("Build Another", "index"),
        ])

    return Page(state, content)


@route
def debug_view(state: State) -> Page:
    """Show raw LLM response and full state for debugging."""
    content = [
        "**Debug: Raw LLM Response**",
        LineBreak(),
    ]

    raw = state.last_raw_response or "<no raw response available>"
    # Show raw response in a preformatted block
    content.append("Raw response:")
    content.append(raw)
    content.append(LineBreak())
    content.append("Current state:")
    # Show state fields
    content.append(f"last_description: {state.last_description}")
    if state.last_website:
        content.append("last_website.html:")
        content.append(state.last_website.website_html)
    else:
        content.append("last_website: None")

    content.append(LineBreak())
    content.append(Button("Back", "index"))
    return Page(state, content)


start_server(State(None, "", None))
