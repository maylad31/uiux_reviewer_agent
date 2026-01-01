from haystack.components.agents import Agent
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.dataclasses import ChatMessage,ImageContent
from haystack.tools import Tool
import shared_state 
import gradio as gr
from dotenv import load_dotenv
from utils import capture_page,html_analyzer,image_weight_analyzer,get_readability_score
from PIL import Image
from io import BytesIO
import base64

load_dotenv()

def workflow(url,progress=gr.Progress()):
    progress(0.01,"Started")
    web_data = capture_page(url)
    shared_state.URL_DATA[url] = web_data
    tools = [
        Tool(
            name="html_analyzer",
            description="Returns html structure of the landing page.",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "url of the landing page"}
                },
                "required": ["url"]
            },
            function=html_analyzer
        ),
        Tool(
            name="get_readability_score",
            description="Returns readability score of the landing page.",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "url of the landing page"}
                },
                "required": ["url"]
            },
            function=get_readability_score
        ),
        Tool(
            name="image_weight_analyzer",
            description="Returns image count and largest image size on the landing page.",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "url of the landing page"}
                },
                "required": ["url"]
            },
            function=image_weight_analyzer
        )
    ]

    agent = Agent(
        chat_generator=OpenAIChatGenerator(model="gpt-4o-mini",generation_kwargs={"max_completion_tokens":3000}),
        tools=tools,
        max_agent_steps = 5
    )

    prompt = f"""
    You are an expert in UI/UX. You are given desktop and mobile views, along with performance data, for a landing page. First, determine the domain based on the page content, and then analyze the landing page from a UI/UX perspective.

    Make sure to consider the domain during your analysis. For example, a finance website may have very different requirements compared to a travel website. Some websites require higher readability, while others should focus more on wonderful visuals and engagement and less on readability.

    You are also provided with tools to:

    - analyze the HTML structure,

    - extract image-related data, and

    - calculate a readability score.

    The use of these tools is optional. Decide which tools are needed and use them if they help you provide better feedback.

    Provide both positive and negative feedback on the following aspects, considering both desktop and mobile views:

    - Content (how suitable and effective the content is for the given domain)

    - Layout (layout quality, CTAs and ease of navigation)

    - Visuals (design, responsiveness, and visual quality, considering the domain)

    - Actionable improvements

    Do not make up information. Speak like a ui/ux expert using simple informal english. Return the feedback in Markdown format.
    URL: {url}
    Performance: {web_data[2]}
    """
    screenshots = web_data[0]
    desktop_content = ImageContent(base64_image=f"{screenshots[0]}",detail="low")
    mobile_content =  ImageContent(base64_image=f"{screenshots[1]}",detail="low")
    progress(0.5,"Sent data to agent")
    result = agent.run(
        messages=[ChatMessage.from_user(content_parts=[prompt,desktop_content,mobile_content])]
    )
    feedback = result["messages"][-1].text
    print(result["messages"])
    all_messages = "\n".join([str(message.tool_calls) for message in result["messages"] if message.tool_calls])
    pil_images = [Image.open(BytesIO(base64.b64decode(screenshots[0]))),Image.open(BytesIO(base64.b64decode(screenshots[1])))]
    return feedback,pil_images, all_messages



with gr.Blocks(title="Landing page UI/UX Quality Reviewer") as demo:
    gr.Markdown(
        """
        # Landing page UI/UX Reviewer
        """
    )

    url_input = gr.Textbox(
        label="Landing Page URL",
        placeholder="https://example.com"
    )

    analyze_btn = gr.Button("Analyze")
    messages = gr.Textbox(lines=5,label="Tool calls:")
    gallery = gr.Gallery(
        label="Page Screenshots",
        columns=2,
        object_fit="contain",
        height="auto"
    )
    feedback_title = gr.HTML("<h1>Feedback:</h1>")
    feedback = gr.Markdown()
    analyze_btn.click(
        fn=workflow,
        inputs=url_input,
        outputs=[feedback,gallery, messages],
    )


demo.queue().launch()

