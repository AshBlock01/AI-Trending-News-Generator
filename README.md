# AI Trending News Draft Generator

An interactive Streamlit app that scrapes trending news articles from Google News and generates high-quality, Gen-Z-friendly draft blog posts using Firecrawl and Pydantic-AI (Gemini models). This project is perfect for content creators looking for fast and AI-driven draft creation.

## **Features**

- **Google News Scraper**  
  Fetch trending articles based on your query.

- **Firecrawl Integration**  
  Extract clean and readable content from articles.

- **AI-Generated Blog Drafts**  
  Use Pydantic-AI and Gemini models to produce engaging, structured, and SEO-friendly blog drafts.

- **Streamlit Interface**  
  User-friendly app with configurable API keys, scraping limits, and AI model options.

---

## Requirements

- Python 3.7+
- Libraries in requirements.txt

## Setup & Usage

1. **Clone the repository**:
   ```bash
   git clone https://github.com/AshBlock01/AI-Trending-News-Generator.git
   cd AI-Trending-News-Generator
   pip install -r requirements.txt
   streamlit run src/app.py
   ```