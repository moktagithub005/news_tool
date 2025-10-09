import streamlit as st
import requests
from datetime import datetime, timedelta
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_openai import OpenAI
from langchain.schema import Document
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from langchain.chains import RetrievalQA
import re
import pandas as pd
from typing import List, Dict
import os
import PyPDF2
import io
from datetime import date

# Page configuration
st.set_page_config(
    page_title="UPSC Daily News Analyzer",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
.main-header {
    font-size: 2.5rem;
    color: #1f77b4;
    text-align: center;
    margin-bottom: 2rem;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
}
.category-header {
    font-size: 1.5rem;
    color: #ff7f0e;
    border-bottom: 2px solid #ff7f0e;
    padding-bottom: 0.5rem;
    margin: 1rem 0;
}
.article-card {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 1rem 0;
    border-left: 4px solid #1f77b4;
}
.upsc-summary {
    background-color: #e8f5e8;
    padding: 1.5rem;
    border-radius: 0.5rem;
    border-left: 4px solid #28a745;
    margin: 1rem 0;
}
.key-points {
    background-color: #fff3cd;
    padding: 1.5rem;
    border-radius: 0.5rem;
    border-left: 4px solid #ffc107;
    margin: 1rem 0;
}
.important-dates {
    background-color: #d1ecf1;
    padding: 1.5rem;
    border-radius: 0.5rem;
    border-left: 4px solid #17a2b8;
    margin: 1rem 0;
}
.laws-acts {
    background-color: #f8d7da;
    padding: 1.5rem;
    border-radius: 0.5rem;
    border-left: 4px solid #dc3545;
    margin: 1rem 0;
}
.chat-container {
    background-color: #f1f3f4;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 0.5rem 0;
}
.user-message {
    background-color: #e3f2fd;
    padding: 0.8rem;
    border-radius: 1rem;
    margin: 0.5rem 0;
    text-align: right;
}
.bot-message {
    background-color: #f1f8e9;
    padding: 0.8rem;
    border-radius: 1rem;
    margin: 0.5rem 0;
}
</style>
""", unsafe_allow_html=True)

class UPSCNewsAnalyzer:
    def __init__(self, newsapi_key: str, openai_key: str = None):
        self.newsapi_key = newsapi_key
        self.openai_key = openai_key
        self.base_url = "https://newsapi.org/v2/everything"
        
        # Initialize LangChain components
        if openai_key:
            self.llm = OpenAI(temperature=0.3, openai_api_key=openai_key, max_tokens=1000)
            self.embeddings = OpenAIEmbeddings(openai_api_key=openai_key)
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=2000,
                chunk_overlap=200,
                length_function=len
            )
            self._setup_prompts()
        
        # UPSC-relevant categories
        self.upsc_categories = {
            'polity': 'India AND (government OR politics OR parliament OR constitution OR supreme court OR election)',
            'economy': 'India AND (economy OR budget OR GDP OR inflation OR RBI OR finance OR tax)',
            'international': 'India AND (international OR foreign policy OR diplomacy OR trade OR china OR pakistan)',
            'environment': 'India AND (environment OR climate OR pollution OR forest OR wildlife OR renewable)',
            'science_tech': 'India AND (science OR technology OR space OR ISRO OR research OR innovation)',
            'social': 'India AND (education OR health OR welfare OR scheme OR poverty OR rural development)',
            'security': 'India AND (security OR defence OR military OR terrorism OR border OR army)',
            'geography': 'India AND (disaster OR flood OR earthquake OR cyclone OR drought OR weather)'
        }
        
        # Initialize knowledge base
        if 'knowledge_base' not in st.session_state:
            st.session_state.knowledge_base = None
    
    def _setup_prompts(self):
        """Setup LangChain prompts for UPSC analysis"""
        
        # Enhanced UPSC analysis prompt
        self.enhanced_analysis_prompt = PromptTemplate(
            input_variables=["article_text", "category"],
            template="""
You are an expert UPSC mentor and current affairs analyst. Analyze this news article and provide a comprehensive breakdown for UPSC preparation.

ARTICLE CATEGORY: {category}
ARTICLE TEXT: {article_text}

Provide your analysis in this EXACT format:

## 🎯 KEY BULLET POINTS:
• [Point 1 - Most important takeaway]
• [Point 2 - Government action/policy mentioned]
• [Point 3 - Statistical data/numbers if any]
• [Point 4 - Impact on citizens/economy/society]
• [Point 5 - Future implications]

## 📅 IMPORTANT DATES & DEADLINES:
• [Date 1]: [Event/Deadline/Launch]
• [Date 2]: [Important milestone mentioned]
• [Timeline]: [Any duration/period mentioned]
(If no specific dates, mention "No specific dates mentioned in this article")

## ⚖️ LAWS, ACTS & CONSTITUTIONAL PROVISIONS:
• [Any law/act mentioned]: [Brief explanation]
• [Constitutional Article]: [If referenced]
• [Policy/Scheme]: [Details and significance]
• [Institution/Body]: [Role and importance]
(If none mentioned, state "No specific laws/acts mentioned")

## 🏛️ GOVERNMENT ACTIONS & DECISIONS:
• Ministry/Department involved: [Details]
• Policy changes: [What changed and why]
• Budget allocation: [If mentioned]
• Implementation timeline: [When it takes effect]

## 🌍 UPSC INTERVIEW RELEVANCE:
• Current topic for interview: [How this relates to interview questions]
• Possible questions: [2-3 questions that could be asked]
• Connection to other issues: [Related current topics]

## 📚 STATIC KNOWLEDGE CONNECTIONS:
• Geography: [Location/regional implications]
• Polity: [Constitutional/governance aspects]
• Economy: [Economic implications]
• History: [Historical context if any]

## 🎓 EXAM UTILITY:
• Prelims relevance: [Factual points for MCQs]
• Mains relevance: [Essay/answer writing angles]
• Optional subject relevance: [If applicable]

Be specific, factual, and focus on exam utility. Use bullet points throughout.
"""
        )
        
        # PDF analysis prompt
        self.pdf_analysis_prompt = PromptTemplate(
            input_variables=["pdf_text", "user_query"],
            template="""
You are analyzing a newspaper/document for UPSC preparation. 

DOCUMENT CONTENT: {pdf_text}

USER QUERY: {user_query}

Provide a comprehensive answer focusing on:
1. Direct response to the query
2. UPSC-relevant points from the content
3. Important dates, names, numbers
4. Government policies/actions mentioned
5. Exam relevance and potential questions

Format your response with clear headings and bullet points for easy reading.
"""
        )
        
        # Chatbot prompt for interactive queries
        self.chatbot_prompt = PromptTemplate(
            input_variables=["context", "question"],
            template="""
You are an AI assistant specialized in UPSC current affairs and interview preparation. Use the following context from recent news articles and your knowledge to answer the question.

CONTEXT FROM RECENT NEWS: {context}

QUESTION: {question}

Guidelines for your response:
- Be specific and factual
- Include dates, numbers, and names where relevant
- Connect to UPSC syllabus topics
- Suggest follow-up topics to study
- For interview questions, provide structured answers
- Use bullet points for clarity

Answer:
"""
        )
    
    def extract_pdf_text(self, pdf_file):
        """Extract text from uploaded PDF"""
        try:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            st.error(f"Error reading PDF: {str(e)}")
            return None
    
    def analyze_pdf_content(self, pdf_text: str, user_query: str = "Provide a UPSC-focused summary") -> str:
        """Analyze PDF content based on user query"""
        if not self.openai_key:
            return "PDF analysis requires OpenAI API key. Please add it in the sidebar."
        
        try:
            # Split text if too long
            docs = self.text_splitter.create_documents([pdf_text])
            
            # Analyze with LLM
            chain = LLMChain(llm=self.llm, prompt=self.pdf_analysis_prompt)
            
            if len(docs) == 1:
                analysis = chain.run(pdf_text=docs[0].page_content, user_query=user_query)
            else:
                # For multiple chunks, analyze each and combine
                analyses = []
                for i, doc in enumerate(docs[:3]):  # Limit to first 3 chunks
                    chunk_analysis = chain.run(pdf_text=doc.page_content, user_query=f"{user_query} (Part {i+1})")
                    analyses.append(f"**Part {i+1}:**\n{chunk_analysis}")
                analysis = "\n\n".join(analyses)
            
            return analysis
            
        except Exception as e:
            return f"Error analyzing PDF: {str(e)}"
    
    def create_knowledge_base(self, articles: List[Dict]):
        """Create a vector knowledge base from articles for chatbot"""
        if not self.openai_key:
            return None
        
        try:
            # Prepare documents
            documents = []
            for article in articles:
                content = f"""
                Title: {article.get('title', '')}
                Category: {article.get('category', 'general')}
                Published: {article.get('publishedAt', '')}
                Source: {article.get('source', {}).get('name', '')}
                Description: {article.get('description', '')}
                Content: {article.get('content', '')}
                """
                documents.append(Document(page_content=content))
            
            # Create vector store
            if documents:
                vectorstore = FAISS.from_documents(documents, self.embeddings)
                return vectorstore
            
        except Exception as e:
            st.error(f"Error creating knowledge base: {str(e)}")
        
        return None
    
    def chat_with_news(self, question: str, knowledge_base) -> str:
        """Chat with the news knowledge base"""
        if not self.openai_key or not knowledge_base:
            return "Chat feature requires OpenAI API key and news data. Please fetch news first."
        
        try:
            # Create retrieval chain
            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=knowledge_base.as_retriever(search_kwargs={"k": 3}),
                chain_type_kwargs={"prompt": self.chatbot_prompt}
            )
            
            response = qa_chain.run(question)
            return response
            
        except Exception as e:
            return f"Error in chat: {str(e)}"
    
    def fetch_news_by_category(self, category: str, days_back: int = 3, max_articles: int = 10) -> List[Dict]:
        """Fetch news articles for a specific UPSC category"""
        try:
            query = self.upsc_categories.get(category, f'India AND {category}')
            
            end_date = datetime.today()
            start_date = end_date - timedelta(days=days_back)
            
            params = {
                'q': query,
                'from': start_date.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d'),
                'sortBy': 'publishedAt',
                'pageSize': max_articles * 2,
                'language': 'en',
                'apiKey': self.newsapi_key
            }
            
            response = requests.get(self.base_url, params=params)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            
            if data.get("status") != "ok":
                return []
            
            articles = data.get("articles", [])
            filtered_articles = self._filter_indian_articles(articles)[:max_articles]
            
            # Add category info to articles
            for article in filtered_articles:
                article['category'] = category
            
            return filtered_articles
            
        except Exception as e:
            st.error(f"Error fetching {category} news: {str(e)}")
            return []
    
    def _filter_indian_articles(self, articles: List[Dict]) -> List[Dict]:
        """Filter articles to ensure they're India-related"""
        india_keywords = [
            'india', 'indian', 'delhi', 'mumbai', 'bangalore', 'kolkata', 'chennai',
            'modi', 'parliament', 'lok sabha', 'rajya sabha', 'bjp', 'congress',
            'hindustan', 'bharat', 'new delhi', 'maharashtra', 'gujarat', 'karnataka',
            'supreme court', 'high court', 'rbi', 'sebi', 'niti aayog'
        ]
        
        filtered = []
        for article in articles:
            title = article.get("title", "").lower()
            description = article.get("description", "").lower()
            content = article.get("content", "").lower()
            source = article.get("source", {}).get("name", "").lower()
            
            text_to_check = f"{title} {description} {content} {source}"
            
            if any(keyword in text_to_check for keyword in india_keywords):
                article['upsc_relevance'] = sum(1 for keyword in india_keywords if keyword in text_to_check)
                filtered.append(article)
        
        filtered.sort(key=lambda x: x.get('upsc_relevance', 0), reverse=True)
        return filtered
    
    def enhanced_upsc_analysis(self, article: Dict, category: str) -> Dict:
        """Enhanced UPSC analysis with detailed breakdown"""
        if not self.openai_key:
            return self._create_basic_analysis(article, category)
        
        try:
            article_text = f"""
            Title: {article.get('title', '')}
            Description: {article.get('description', '')}
            Content: {article.get('content', '')}
            Source: {article.get('source', {}).get('name', '')}
            Published: {article.get('publishedAt', '')}
            """
            
            chain = LLMChain(llm=self.llm, prompt=self.enhanced_analysis_prompt)
            analysis = chain.run(article_text=article_text, category=category)
            
            return {
                'analysis': analysis,
                'processed_with_ai': True,
                'article_title': article.get('title', ''),
                'article_url': article.get('url', '')
            }
            
        except Exception as e:
            st.error(f"Analysis error: {str(e)}")
            return self._create_basic_analysis(article, category)
    
    def _create_basic_analysis(self, article: Dict, category: str) -> Dict:
        """Create basic analysis when AI is not available"""
        title = article.get('title', '')
        description = article.get('description', '')
        
        basic_analysis = f"""
## 🎯 KEY BULLET POINTS:
• {title}
• {description[:100]}...
• Category: {category.title()}
• Source: {article.get('source', {}).get('name', 'Unknown')}
• Published: {article.get('publishedAt', 'Unknown')}

## 📅 IMPORTANT DATES & DEADLINES:
• Publication Date: {article.get('publishedAt', 'Unknown')}
• (For detailed date analysis, AI analysis is required)

## ⚖️ LAWS, ACTS & CONSTITUTIONAL PROVISIONS:
• (Detailed legal analysis requires AI processing)

## 🏛️ GOVERNMENT ACTIONS & DECISIONS:
• (Comprehensive analysis requires AI processing)

## 🌍 UPSC INTERVIEW RELEVANCE:
• Current affairs topic from {category} category
• (For detailed interview questions, use AI analysis)

*Note: For comprehensive analysis, please add OpenAI API key in sidebar*
"""
        
        return {
            'analysis': basic_analysis,
            'processed_with_ai': False,
            'article_title': title,
            'article_url': article.get('url', '')
        }

def main():
    st.markdown('<h1 class="main-header">🇮🇳 UPSC Daily News Analyzer Pro</h1>', unsafe_allow_html=True)
    st.markdown("*Your comprehensive AI companion for UPSC current affairs preparation*")
    
    # Sidebar configuration
    st.sidebar.header("⚙️ Configuration")
    
    # API Keys
    newsapi_key = st.sidebar.text_input("NewsAPI Key", type="password", value="58857cd8c1f341628b19836dcb69fc26")
    openai_key = st.sidebar.text_input("OpenAI API Key", type="password", help="Required for AI analysis and chat features")
    
    if not newsapi_key:
        st.warning("Please enter your NewsAPI key to continue.")
        return
    
    # Initialize analyzer
    analyzer = UPSCNewsAnalyzer(newsapi_key, openai_key)
    
    # Main navigation
    tab1, tab2, tab3, tab4 = st.tabs(["📰 Daily News Analysis", "📄 PDF Analysis", "💬 AI Chat Assistant", "📚 Saved Content"])
    
    # TAB 1: Daily News Analysis
    with tab1:
        st.sidebar.header("📊 News Analysis Options")
        days_back = st.sidebar.slider("Days to look back", 1, 14, 3)
        articles_per_category = st.sidebar.slider("Articles per category", 2, 8, 4)
        
        selected_categories = st.sidebar.multiselect(
            "Select UPSC Categories",
            list(analyzer.upsc_categories.keys()),
            default=['polity', 'economy']
        )
        
        if st.sidebar.button("🔄 Fetch Latest News", type="primary"):
            if not selected_categories:
                st.warning("Please select at least one category.")
                return
            
            all_articles = []
            category_tabs = st.tabs([cat.replace('_', ' ').title() for cat in selected_categories])
            
            for i, category in enumerate(selected_categories):
                with category_tabs[i]:
                    st.markdown(f'<h2 class="category-header">{category.replace("_", " ").title()} News</h2>', unsafe_allow_html=True)
                    
                    with st.spinner(f"Fetching {category} news..."):
                        articles = analyzer.fetch_news_by_category(category, days_back, articles_per_category)
                    
                    if not articles:
                        st.warning(f"No articles found for {category}")
                        continue
                    
                    all_articles.extend(articles)
                    st.success(f"Found {len(articles)} relevant articles")
                    
                    for idx, article in enumerate(articles):
                        with st.expander(f"📰 {article.get('title', 'No Title')[:80]}...", expanded=False):
                            
                            col1, col2 = st.columns([3, 1])
                            
                            with col1:
                                st.markdown("### 📄 Article Details")
                                st.write(f"**Source:** {article.get('source', {}).get('name', 'Unknown')}")
                                st.write(f"**Published:** {article.get('publishedAt', 'Unknown')}")
                                st.write(f"**Description:** {article.get('description', 'No description')}")
                                
                                if article.get('url'):
                                    st.markdown(f"[🔗 Read Full Article]({article['url']})")
                            
                            with col2:
                                relevance = min(article.get('upsc_relevance', 0) + 3, 10)
                                st.metric("UPSC Relevance", f"{relevance}/10")
                            
                            # Enhanced Analysis Button
                            if st.button(f"🎯 Analyze for UPSC", key=f"analyze_{category}_{idx}", type="primary"):
                                with st.spinner("Performing detailed UPSC analysis..."):
                                    analysis_result = analyzer.enhanced_upsc_analysis(article, category)
                                
                                # Display comprehensive analysis
                                st.markdown('<div class="upsc-summary">', unsafe_allow_html=True)
                                st.markdown("### 🎓 Comprehensive UPSC Analysis")
                                st.markdown(analysis_result['analysis'])
                                st.markdown('</div>', unsafe_allow_html=True)
                                
                                # Save analysis
                                if 'saved_analyses' not in st.session_state:
                                    st.session_state.saved_analyses = []
                                
                                st.session_state.saved_analyses.append({
                                    'title': analysis_result['article_title'],
                                    'category': category,
                                    'analysis': analysis_result['analysis'],
                                    'url': analysis_result['article_url'],
                                    'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
                                    'processed_with_ai': analysis_result['processed_with_ai']
                                })
                                
                                st.success("✅ Analysis completed and saved!")
            
            # Create knowledge base for chat
            if all_articles and openai_key:
                with st.spinner("Building knowledge base for AI chat..."):
                    st.session_state.knowledge_base = analyzer.create_knowledge_base(all_articles)
                    if st.session_state.knowledge_base:
                        st.success("🧠 Knowledge base created! You can now use the AI Chat Assistant.")
    
    # TAB 2: PDF Analysis
    with tab2:
        st.markdown("### 📄 Upload Newspaper PDF for Analysis")
        st.write("Upload PDF files of newspapers (The Hindu, Indian Express, etc.) for UPSC-focused analysis")
        
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
        
        if uploaded_file:
            st.success(f"Uploaded: {uploaded_file.name}")
            
            # Extract text
            with st.spinner("Extracting text from PDF..."):
                pdf_text = analyzer.extract_pdf_text(uploaded_file)
            
            if pdf_text:
                st.info(f"Extracted {len(pdf_text)} characters from PDF")
                
                # Query input
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    user_query = st.text_input(
                        "What would you like to know about this newspaper?",
                        placeholder="e.g., Give me summary of yesterday's news or What are the important government decisions mentioned?"
                    )
                
                with col2:
                    st.write("**Quick Options:**")
                    if st.button("📋 Full Summary"):
                        user_query = "Provide a comprehensive UPSC-focused summary of all important news"
                    if st.button("📅 Important Dates"):
                        user_query = "Extract all important dates, deadlines, and timeline mentioned"
                    if st.button("🏛️ Government Actions"):
                        user_query = "List all government decisions, policies, and actions mentioned"
                
                # Analyze PDF
                if st.button("🔍 Analyze PDF", type="primary") or user_query:
                    if not user_query:
                        user_query = "Provide a UPSC-focused summary"
                    
                    with st.spinner("Analyzing PDF content..."):
                        analysis = analyzer.analyze_pdf_content(pdf_text, user_query)
                    
                    st.markdown('<div class="upsc-summary">', unsafe_allow_html=True)
                    st.markdown("### 📊 PDF Analysis Results")
                    st.markdown(analysis)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Save PDF analysis
                    if 'saved_pdf_analyses' not in st.session_state:
                        st.session_state.saved_pdf_analyses = []
                    
                    st.session_state.saved_pdf_analyses.append({
                        'filename': uploaded_file.name,
                        'query': user_query,
                        'analysis': analysis,
                        'date': datetime.now().strftime('%Y-%m-%d %H:%M')
                    })
                    
                    st.success("✅ PDF analysis saved!")
    
    # TAB 3: AI Chat Assistant
    with tab3:
        st.markdown("### 💬 AI Chat Assistant for UPSC Queries")
        st.write("Ask questions about current affairs, get interview preparation help, and more!")
        
        if not openai_key:
            st.warning("OpenAI API key required for chat functionality.")
            return
        
        # Initialize chat history
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        # Predefined question buttons
        st.markdown("#### 🚀 Quick Questions:")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📰 Today's Key News"):
                question = "What are the most important news items for UPSC from today?"
                st.session_state.chat_history.append({"user": question, "bot": "Processing..."})
        
        with col2:
            if st.button("🎤 Interview Topics"):
                question = "What current topics should I prepare for UPSC interview?"
                st.session_state.chat_history.append({"user": question, "bot": "Processing..."})
        
        with col3:
            if st.button("📚 Static GK Links"):
                question = "Connect today's news with static GK topics for better understanding"
                st.session_state.chat_history.append({"user": question, "bot": "Processing..."})
        
        with col4:
            if st.button("🎯 Exam Strategy"):
                question = "How can I use current affairs effectively in UPSC exam?"
                st.session_state.chat_history.append({"user": question, "bot": "Processing..."})
        
        # Chat input
        user_question = st.text_input("Ask me anything about current affairs, UPSC preparation, or today's news:", key="chat_input")
        
        if st.button("💬 Ask", type="primary") or user_question:
            if user_question:
                if st.session_state.knowledge_base:
                    with st.spinner("Thinking..."):
                        response = analyzer.chat_with_news(user_question, st.session_state.knowledge_base)
                    
                    st.session_state.chat_history.append({"user": user_question, "bot": response})
                else:
                    st.warning("Please fetch news first to build the knowledge base for better responses.")
                    # Fallback - direct LLM query
                    with st.spinner("Generating response..."):
                        simple_chain = LLMChain(llm=analyzer.llm, prompt=PromptTemplate(
                            input_variables=["question"],
                            template="You are a UPSC mentor. Answer this question with focus on exam preparation: {question}"
                        ))
                        response = simple_chain.run(question=user_question)
                    
                    st.session_state.chat_history.append({"user": user_question, "bot": response})
        
        # Display chat history
        if st.session_state.chat_history:
            st.markdown("#### 💬 Chat History:")
            for i, chat in enumerate(reversed(st.session_state.chat_history[-5:])):  # Show last 5 chats
                st.markdown(f'<div class="user-message">🙋‍♂️ <strong>You:</strong> {chat["user"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="bot-message">🤖 <strong>AI Assistant:</strong><br>{chat["bot"]}</div>', unsafe_allow_html=True)
            
            if st.button("🗑️ Clear Chat History"):
                st.session_state.chat_history = []
                st.rerun()
    
    # TAB 4: Saved Content
    with tab4:
        st.markdown("### 📚 Your Saved Analyses & Content")
        
        # Saved news analyses
        if 'saved_analyses' in st.session_state and st.session_state.saved_analyses:
            st.markdown("#### 📰 Saved News Analyses")
            for i, saved in enumerate(st.session_state.saved_analyses):
                with st.expander(f"📄 {saved['title'][:60]}... - {saved['category']} ({saved['date']})"):
                    st.markdown(saved['analysis'])
                    if saved.get('url'):
                        st.markdown(f"[🔗 Original Article]({saved['url']})")
                    ai_badge = "🤖 AI Processed" if saved.get('processed_with_ai') else "📝 Basic Analysis"
                    st.badge(ai_badge)
        
        # Saved PDF analyses
        if 'saved_pdf_analyses' in st.session_state and st.session_state.saved_pdf_analyses:
            st.markdown("#### 📄 Saved PDF Analyses")
            for i, saved in enumerate(st.session_state.saved_pdf_analyses):
                with st.expander(f"📁 {saved['filename']} - {saved['date']}"):
                    st.write(f"**Query:** {saved['query']}")
                    st.markdown("**Analysis:**")
                    st.markdown(saved['analysis'])
        
        # Export options
        if ('saved_analyses' in st.session_state and st.session_state.saved_analyses) or \
           ('saved_pdf_analyses' in st.session_state and st.session_state.saved_pdf_analyses):
            
            st.markdown("#### 📤 Export Options")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📄 Export as Text"):
                    export_text = "# UPSC News Analysis Export\n\n"
                    export_text += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                    
                    if 'saved_analyses' in st.session_state:
                        export_text += "## News Articles Analysis\n\n"
                        for saved in st.session_state.saved_analyses:
                            export_text += f"### {saved['title']}\n"
                            export_text += f"Category: {saved['category']}\n"
                            export_text += f"Date: {saved['date']}\n"
                            export_text += f"{saved['analysis']}\n\n"
                    
                    if 'saved_pdf_analyses' in st.session_state:
                        export_text += "## PDF Analysis\n\n"
                        for saved in st.session_state.saved_pdf_analyses:
                            export_text += f"### {saved['filename']}\n"
                            export_text += f"Query: {saved['query']}\n"
                            export_text += f"Date: {saved['date']}\n"
                            export_text += f"{saved['analysis']}\n\n"
                    
                    st.download_button(
                        label="⬇️ Download Export",
                        data=export_text,
                        file_name=f"upsc_analysis_{datetime.now().strftime('%Y%m%d')}.txt",
                        mime="text/plain"
                    )
            
            with col2:
                if st.button("🗑️ Clear All Saved Content"):
                    st.session_state.saved_analyses = []
                    st.session_state.saved_pdf_analyses = []
                    st.success("All saved content cleared!")
                    st.rerun()
            
            with col3:
                total_items = len(st.session_state.get('saved_analyses', [])) + len(st.session_state.get('saved_pdf_analyses', []))
                st.metric("Total Saved Items", total_items)
        
        else:
            st.info("No saved content yet. Analyze some articles or PDFs first!")
    
    # Sidebar footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎯 Daily Study Routine")
    st.sidebar.write("✅ Check 2-3 categories daily")
    st.sidebar.write("✅ Focus on 7+ relevance articles")
    st.sidebar.write("✅ Use chat for doubt clarification")
    st.sidebar.write("✅ Export weekly for revision")
    
    # Main footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <h4>🏆 UPSC Success Features</h4>
        <p>📰 <strong>Smart News Analysis</strong> | 📄 <strong>PDF Processing</strong> | 💬 <strong>AI Chat Assistant</strong> | 📚 <strong>Content Management</strong></p>
        <p><em>Designed by UPSC experts for serious aspirants</em></p>
        <p>💡 <strong>Pro Tip:</strong> Use this tool for 20-25 minutes daily. Quality analysis beats quantity reading!</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()