#!/bin/bash
# build.sh - Render.com build script

set -e  # Exit on error

echo "🔧 Starting build process..."

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install dependencies in order
echo "📦 Installing core dependencies..."
pip install python-dotenv requests pandas

echo "📦 Installing LangChain stack..."
pip install langchain-core langchain-community langchain langsmith

echo "📦 Installing LLM providers..."
pip install groq langchain-groq langchain-openai

echo "📦 Installing remaining dependencies..."
pip install -r requirements.txt

echo "✅ Build complete!"