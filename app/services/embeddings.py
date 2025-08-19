import os
from dotenv import load_dotenv
import google.generativeai as genai
from chromadb import PersistentClient
from chromadb.utils.embedding_functions import EmbeddingFunction
from langchain.text_splitter import SentenceTransformersTokenTextSplitter

# Load environment variables
load_dotenv()
api_key = os.getenv("EMBEDDING_KEY")

if not api_key:
    raise ValueError("GOOGLE_API_KEY is not set in the .env file")

# Configure the generative AI client
genai.configure(api_key=api_key)

# Initialize Chroma persistent client
persist_directory = "chroma_db"
os.makedirs(persist_directory, exist_ok=True)
chroma_client = PersistentClient(path=persist_directory)


class GeminiEmbedding(EmbeddingFunction):
    """
    Custom embedding function using Google Gemini embeddings.

    This class implements the ChromaDB `EmbeddingFunction` interface
    to generate vector embeddings for given texts using the
    `models/embedding-001` model from Google Generative AI.

    Methods
    -------
    __call__(texts: list[str]) -> list[list[float]]:
        Takes a list of texts and returns their corresponding embeddings.
    """

    def __call__(self, texts):
        """
        Generate embeddings for a list of input texts.

        Parameters
        ----------
        texts : list[str]
            A list of text strings to embed.

        Returns
        -------
        list[list[float]]
            A list of embedding vectors corresponding to each input text.
        """
        embeddings = []
        for text in texts:
            response = genai.embed_content(
                model="models/embedding-001",
                content=text,
                task_type="retrieval_document",
            )
            embeddings.append(response["embedding"])
        return embeddings


def embed_and_store_transcript(transcript: str, video_title: str):
    """
    Splits a transcript into smaller chunks, generates embeddings,
    and stores them in a persistent ChromaDB collection.

    Parameters
    ----------
    transcript : str
        The transcript text to be embedded and stored.
    video_title : str
        The title of the video, used to create/retrieve a ChromaDB collection.

    Process
    -------
    1. Splits transcript into overlapping chunks using SentenceTransformersTokenTextSplitter.
    2. Generates embeddings for each chunk using GeminiEmbedding.
    3. Stores the chunks and embeddings in ChromaDB under a collection
       named after the video title.

    Returns
    -------
    None
    """
    splitter = SentenceTransformersTokenTextSplitter(
        chunk_size=1000,
        chunk_overlap=50,
    )
    chunks = splitter.split_text(transcript)

    embedding_fn = GeminiEmbedding()
    collection = chroma_client.get_or_create_collection(
        name=video_title.replace(" ", "_"),
        embedding_function=embedding_fn,
    )

    collection.add(
        documents=chunks,
        ids=[f"{video_title}_{i}" for i in range(len(chunks))],
    )
