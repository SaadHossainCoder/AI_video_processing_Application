from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

import os
import time

MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "open-mistral-nemo")

def get_llm():
    return ChatMistralAI(model=MISTRAL_MODEL, mistral_api_key=os.getenv("MISTRAL_API_KEY"), temperature=0.3)


def split_transcript(transcript: str) -> list:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=4000,
        chunk_overlap=200
    )

    return splitter.split_text(transcript)

def summarize(transcript: str) -> str:
    llm = get_llm()

    chunks = split_transcript(transcript)

    # If short, summarize directly in 1 call to save API calls and avoid rate limits
    if len(chunks) <= 1:
        direct_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert meeting summarizer. Provide a clear, comprehensive meeting summary in bullet points."),
            ("human", "{text}"),
        ])
        direct_chain = direct_prompt | llm | StrOutputParser()
        return direct_chain.invoke({"text": transcript})

    map_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system", 
                "Summarize this portion of a meeting transcript concisely."
            ),
            ("human", "{text}"), 
        ]
    )

    map_chain = map_prompt | llm | StrOutputParser()

    chunk_summaries = []
    for c in chunks:
        chunk_summaries.append(map_chain.invoke({"text": c}))
        time.sleep(0.5)  # safe pacing for free tier rate limits

    combined = "\n\n".join(chunk_summaries)

    combined_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert meeting summarizer. Combine these partial summaries "
                "into one final professional meeting summary in bullet points.",
            ),
            ("human","{text}"),
        ]
    ) 

    combined_chain =(
        RunnablePassthrough() | RunnableLambda(lambda x:{"text":x}) | combined_prompt | llm | StrOutputParser()
    )

    return combined_chain.invoke(combined) 


def generate_title(transcript : str) -> str:
    llm = get_llm()

    

    title_chain = (
        RunnablePassthrough() | RunnableLambda(lambda x:{"text":x}) | 
        ChatPromptTemplate.from_messages([
             (
                "system",
                "Based on the meeting transcript, generate a short professional meeting title "
                "(max 8 words). Only return the title, nothing else.",
            ),
            ("human", "{text}"),
        ])
        | llm
        |StrOutputParser()
    )

    return title_chain.invoke(transcript[:2000])