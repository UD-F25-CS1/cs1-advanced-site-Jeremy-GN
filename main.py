from drafter import set_site_information, hide_debug_information, set_website_title, set_website_framed, route, Page, TextArea, LineBreak, Button, start_server
from dataclasses import dataclass
from drafter.llm import LLMMessage, LLMResponse, call_gemini, set_gemini_server
from typing import Optional



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

    # Call Gemini to generate the website
    messages = [LLMMessage("user", prompt)]
    result = call_gemini(messages)

    # Parse the response and create a WebsiteBuild
    if isinstance(result, LLMResponse):
        new_website = parse_website_response(result.content)
        new_state = State(new_website, description)
    else:
        # Error occurred, show error message
        error_html = f"<html><body><h1>Error building website</h1><p>{result.message}</p></body></html>"
        new_website = WebsiteBuild(error_html, "", "")
        new_state = State(new_website, description)

    return show_builder(new_state)


def show_builder(state: State) -> Page:
    """Display the website builder interface."""
    content = [
        "Describe the website you want to build:",
        TextArea("description", "", rows=5, cols=50),
        LineBreak(),
        Button("Build Website", build_website), # type: ignore
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


start_server(State(None, ""))
