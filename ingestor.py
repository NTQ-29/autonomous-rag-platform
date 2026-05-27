import os
from typing import List, Dict, Any
from io import BytesIO
import tiktoken
from pypdf import PdfReader
from docx import Document
import structlog

# Initialize structured logging for transparent cloud monitoring
logger = structlog.get_logger()

class CloudDocumentIngestor:
    def __init__(self, target_model: str = "text-embedding-3-small"):
        # Grab the correct tokenizer tokenizer based on your target embedding model
        self.tokenizer = tiktoken.encoding_for_model(target_model)
        
    def extract_text(self, file_bytes: bytes, file_type: str) -> str:
        """Parses raw bytes into clean strings based on the file extension."""
        text = ""
        try:
            if file_type.lower() == "pdf":
                reader = PdfReader(BytesIO(file_bytes))
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                        
            elif file_type.lower() in ["docx", "doc"]:
                doc = Document(BytesIO(file_bytes))
                for paragraph in doc.paragraphs:
                    if paragraph.text:
                        text += paragraph.text + "\n"
                        
            elif file_type.lower() in ["txt", "md"]:
                text = file_bytes.decode("utf-8")
                
            else:
                logger.warning("unsupported_file_type", file_type=file_type)
                raise ValueError(f"Unsupported file type: {file_type}")
                
            return text.strip()
            
        except Exception as e:
            logger.error("extraction_failed", error=str(e))
            raise e

    def recursive_token_splitter(self, text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[Dict[str, Any]]:
        """
        Splits text based on token boundaries rather than character counts.
        Maintains an intentional overlap to keep semantic context unbroken between chunks.
        """
        tokens = self.tokenizer.encode(text)
        chunks = []
        start_idx = 0
        chunk_id = 0

        while start_idx < len(tokens):
            # Define the window end boundary
            end_idx = min(start_idx + chunk_size, len(tokens))
            chunk_tokens = tokens[start_idx:end_idx]
            
            # Decode back into readable string
            chunk_text = self.tokenizer.decode(chunk_tokens)
            
            chunks.append({
                "chunk_id": chunk_id,
                "text": chunk_text,
                "token_count": len(chunk_tokens)
            })
            
            chunk_id += 1
            # Move the window forward, keeping the overlap
            start_idx += (chunk_size - chunk_overlap)

        logger.info("text_chunking_complete", total_chunks=len(chunks))
        return chunks

# Example execution verification block
if __name__ == "__main__":
    ingestor = CloudDocumentIngestor()
    
    # Mocking a quick markdown file payload
    mock_document = (
        "Autonomous RAG systems use graph execution architectures to handle error loops. "
        "When metadata layers or vector index results show weak semantic alignment with user queries, "
        "the agent structure loops backward to execute a query refinement sub-routine."
    ) * 15  # Artificially padding string size to force a chunk split
    
    mock_bytes = mock_document.encode("utf-8")
    
    print("--- Starting Processing Pipeline ---")
    extracted = ingestor.extract_text(mock_bytes, "md")
    processed_chunks = ingestor.recursive_token_splitter(extracted, chunk_size=50, chunk_overlap=10)
    
    for chunk in processed_chunks[:3]:
        print(f"\n[Chunk {chunk['chunk_id']} | Tokens: {chunk['token_count']}]:")
        print(chunk['text'])
