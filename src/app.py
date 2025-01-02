import streamlit as st
import asyncio
import time
import pandas as pd
import requests

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from firecrawl import FirecrawlApp 
import nest_asyncio

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
nest_asyncio.apply(loop)

async def async_work():
    await asyncio.sleep(1)
    return "Async result"

def run_async_task(coro):
    return loop.run_until_complete(coro)


class DraftPost(BaseModel):
    title: str = Field(description="The title of the blog post")
    content: str = Field(description="The content of the blog post")

system_prompt = """
You are an elite news drafting expert with a deep understanding of current events and trends. Your writing style is engaging, insightful, and tailored to resonate with a Gen-Z audience while maintaining professional standards. 

I have provided you with the following news article content in HTML format scraped from a website. Please perform the following tasks:

1. **Content Extraction:** 
   - Accurately extract the main text content from the HTML.
   - Remove any ads, navigation links, unrelated elements, and boilerplate content to ensure clarity and focus.

2. **Draft Generation:**
   - Create a comprehensive draft blog post based on the extracted content.
   - Ensure the post is **engaging**, **well-structured**, and **informative**, suitable for a general audience with a Gen-Z demographic in mind.
   - Incorporate relevant **statistics**, **quotes**, or **anecdotes** to add depth and credibility.

3. **Headline Creation:**
   - Use the provided title as the headline.
   - Ensure the headline is **attention-grabbing**, **clear**, and **SEO-friendly**.

4. **Organizational Structure:**
   - Divide the post into appropriate sections with **clear headings** and **subheadings**.
   - Use bullet points or numbered lists where applicable to enhance readability.

5. **Tone and Style:**
   - Maintain a **professional**, **informative**, and **conversational** tone throughout the post.
   - Use **active voice** and **concise language** to keep readers engaged.
   - Ensure the content is **free of jargon** unless necessary, and when used, terms should be clearly explained.

6. **Originality and Insight:**
   - Provide **unique insights** or **perspectives** that differentiate the post from existing articles on the topic.
   - Encourage critical thinking by highlighting **implications**, **future trends**, or **potential impacts** related to the news topic.

7. **SEO Optimization:**
   - Naturally incorporate relevant **keywords** to improve search engine visibility.
   - Include **meta descriptions** and **alt text** suggestions for any images, if applicable.

8. **Final Touches:**
   - Proofread the draft to eliminate **grammatical errors**, **typos**, and ensure **coherence**.
   - Ensure the post adheres to a **logical flow**, making it easy for readers to follow and understand.

By following these guidelines, produce a high-quality draft blog post that stands out for its **engagement**, **clarity**, and **expertise** in delivering news content.
"""


def encode_special_characters(text):
    encoded_text = ''
    special_characters = {'&': '%26', '=': '%3D', '+': '%2B', ' ': '%20'}
    for char in text.lower():
        encoded_text += special_characters.get(char, char)
    return encoded_text

def fetch_google_news_articles(query: str, limit=3):
    """
    Fetch Google News article links based on a search query.
    """
    encoded_query = encode_special_characters(query)
    url = f"https://news.google.com/search?q={encoded_query}&hl=en-US&gl=US&ceid=US%3Aen"

    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    articles = soup.find_all('article')[:limit]

    links = []
    for article in articles:
        link = article.find('a')['href']
        if link.startswith('./articles/'):
            link = link.replace('./articles/', 'https://news.google.com/articles/')
        elif link.startswith('./'):
            link = link.replace('./', 'https://news.google.com/')
        links.append(link)

    return links

def scrape_contents(app: FirecrawlApp, links):
    """
    Use Firecrawl to scrape the contents of each link.
    """
    contents = []
    for link in links:
        try:
            scrape_result = app.scrape_url(
                link,
                params={'formats': ['markdown', 'html'], "waitFor": 20000}
            )
            contents.append(scrape_result)
            time.sleep(30)  # short delay to avoid rate limiting
        except Exception as e:
            contents.append(f"Error scraping content: {e}")
    return contents

async def generate_draft_post(scraped_content: str, agent: Agent) -> DraftPost:
    # """
    # Asynchronously generate a draft post from scraped content using the provided agent.
    # """
    prompt = f"Generate a draft blog post based on the following content:\n\n{scraped_content}"
    result = await agent.run(prompt)

    if hasattr(result, 'data') and result.data:
        return result.data
    else:
        raise AttributeError("Expected attributes 'title' and 'content' not found in RunResult data.")

async def run_generation_pipeline(query: str, pages_to_scrape: int, firecrawl_key: str, gemini_key: str, model_name: str):
    # """
    # Asynchronously fetch, scrape, and generate draft posts for a given query.

    # :param query: The news search query
    # :param pages_to_scrape: The number of articles/pages to scrape
    # :param firecrawl_key: Firecrawl API key
    # :param gemini_key: Gemini (Pydantic-AI) API key
    # :param model_name: The Gemini model to use
    # """
    app = FirecrawlApp(api_key=firecrawl_key)

    model = GeminiModel(model_name, api_key=gemini_key)

    # Create the Pydantic-AI Agent
    agent = Agent(
        model=model,
        result_type=DraftPost,
        system_prompt=system_prompt
    )

    links = fetch_google_news_articles(query, limit=pages_to_scrape)

    # Scrape contents
    scraped_contents = scrape_contents(app, links)

    # Generate draft posts
    tasks = [generate_draft_post(content, agent) for content in scraped_contents]
    draft_posts = await asyncio.gather(*tasks)

    rows = []
    for link, post in zip(links, draft_posts):
        rows.append({
            "URL": link,
            "Title": post.title,
            "Content": post.content
        })
    return pd.DataFrame(rows)

def format_llm_markdown_output(raw_text: str) -> str:
    """
    Convert literal '\\n' into real newlines so Streamlit markdown can parse
    headings, bullet points, and paragraphs correctly.
    """
    return raw_text.replace("\\n", "\n")

def display_post(post_number: int, title: str, url: str, content: str):
    """
    Display a single post with a title, clickable URL, 
    and full content inside a collapsible expander.
    """
    with st.expander(f"Post #{post_number}: {title}", expanded=False):
        st.markdown(f"[**View Source**]({url})")
        formatted_content = format_llm_markdown_output(content)
        st.markdown(formatted_content)

# --------------------------
# Streamlit App
# --------------------------
def main():
    # st.title("Generate Latest AI News Drafts with Pydantic-AI and Firecrawl")
    st.title("AI Trending News Draft Generator powered by Pydantic-AI and Firecrawl")

    st.markdown("Enter a search query to scrape latest trending News and generate AI-based draft posts.")

    st.sidebar.title("Configuration / API Keys")
    firecrawl_key = st.sidebar.text_input("Firecrawl API Key", type="password")
    gemini_key = st.sidebar.text_input("Gemini API Key", type="password")
    
    st.sidebar.title("Model & Scraping Settings")
    model_name = st.sidebar.selectbox(
        "Select Gemini Model",
        ["gemini-2.0-flash-exp"]  # add more if you have them
    )
    pages_to_scrape = st.sidebar.slider("Number of Pages to Scrape", 1, 10, 2)

    query = st.text_input("Search Query", value="AI in 2025")

    if st.button("Generate Draft Posts"):
        if not firecrawl_key:
            st.warning("Please enter your Firecrawl API Key in the sidebar.")
            return
        if not gemini_key:
            st.warning("Please enter your Gemini API Key in the sidebar.")
            return
        
        with st.spinner("Agents are working hard on it... This may take more than a minute. We need to play nice with the anti-bot measures."):
            df = run_async_task(
                run_generation_pipeline(query, pages_to_scrape, firecrawl_key, gemini_key, model_name)
            )

        st.success("Draft posts generated!")
        st.markdown("Below are the AI-generated posts based on the scraped articles:")

        for idx, row in df.iterrows():
            display_post(
                post_number=idx + 1,
                title=row["Title"],
                url=row["URL"],
                content=row["Content"]
            )

if __name__ == "__main__":
    main()