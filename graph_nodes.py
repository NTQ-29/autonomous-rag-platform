import os
from typing import Dict, Any, List
from typing_extensions import TypedDict
from openai import OpenAI
import structlog
from ingestor import CloudDocumentIngestor
from schemas import VectorPayload

logger = structlog.get_logger()

# 1. Define the Global State of our Autonomous Agent
class AgentState(TypedDict):
    raw_file_bytes: bytes
    file_type: str
    text_chunks: List[Dict[str, Any]]
    vector_payloads: List[Dict[str, Any]]
    errors: List[str]


# 2. Build the Node Class to encapsulate our actions
class RAGIngestionNodes:
    def __init__(self):
        self.ingestor = CloudDocumentIngestor()
        # Initializing the OpenAI client (or Bedrock) for cloud embeddings
        # In production, this client pulls from your cloud environment variables
        self.ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "mock-key"))

    def parse_and_chunk_node(self, state: AgentState) -> Dict[str, Any]:
        """Node 1: Extracts text from raw bytes and breaks it into semantic token units."""
        logger.info("entering_parse_and_chunk_node")
        try:
            raw_text = self.ingestor.extract_text(
                file_bytes=state["raw_file_bytes"], 
                file_type=state["file_type"]
            )
            chunks = self.ingestor.recursive_token_splitter(raw_text, chunk_size=100, chunk_overlap=20)
            
            # Return updates to add directly to the global state
            return {"text_chunks": chunks, "errors": []}
        except Exception as e:
            return {"errors": [f"Chunking failed: {str(e)}"]}

    def generate_embeddings_node(self, state: AgentState) -> Dict[str, Any]:
        """Node 2: Takes text chunks and transforms them into high-dimensional vector arrays."""
        logger.info("entering_generate_embeddings_node")
        chunks = state.get("text_chunks", [])
        if not chunks:
            return {"errors": ["No text chunks found to embed."]}

        payloads = []
        try:
            # Extract just the raw strings for batch embedding processing
            texts_to_embed = [chunk["text"] for chunk in chunks]
            
            # Cloud API Call to vector space model
            # For testing without a key, we can intercept or mock this
            if os.getenv("OPENAI_API_KEY"):
                response = self.ai_client.embeddings.create(
                    input=texts_to_embed,
                    model="text-embedding-3-small"
                )
                embeddings = [data.embedding for data in response.data]
            else:
                # Fallback mock vectors (1536 dimensions) if running offline in Codespace
                logger.warning("using_mock_embeddings_no_api_key_found")
                embeddings = [[0.012] * 1536 for _ in chunks]

            # Enforce schema mapping to prepare for S3 Vector Bucket transmission
            for idx, chunk in enumerate(chunks):
                payload = VectorPayload(
                    key=f"doc_upload#chunk_{chunk['chunk_id']}",
                    vector=embeddings[idx],
                    metadata={"text_content": chunk["text"], "token_count": chunk["token_count"]}
                )
                payloads.append(payload.model_dump())

            return {"vector_payloads": payloads}
        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            return {"errors": state.get("errors", []) + [f"Embedding failed: {str(e)}"]}
    
    def autonomous_fix_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Node 3: Inspects failures in the state and attempts auto-correction
        (e.g., falling back to a raw text extraction bypass if a complex format failed).
        """
        logger.warning("entering_autonomous_fix_node", active_errors=state.get("errors"))
        
        # Pull existing errors
        current_errors = state.get("errors", [])
        
        # Self-correction logic: If parsing failed, let's attempt to force a raw string fallback 
        # as a safety net so the pipeline can gracefully extract what it can.
        if any("Chunking failed" in err for err in current_errors):
            logger.info("attempting_fallback_raw_decoding")
            try:
                fallback_text = state["raw_file_bytes"].decode("utf-8", errors="ignore")
                chunks = self.ingestor.recursive_token_splitter(fallback_text, chunk_size=100, chunk_overlap=20)
                
                # Clear the catastrophic error since we recovered with a fallback
                return {"text_chunks": chunks, "errors": ["Warning: Recovered via raw-string fallback parsing."]}
            except Exception as e:
                return {"errors": current_errors + [f"Auto-correction fallback failed: {str(e)}"]}
                
        return {"errors": current_errors + ["Unrecoverable pipeline failure."]}
    
    async def transmit_to_cloud_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Node 4: Connects to our decoupled MCP Server microservice as a client
        and transmits the finalized vectors to our AWS S3 Vector Buckets.
        """
        logger.info("entering_transmit_to_cloud_node")
        payloads = state.get("vector_payloads", [])
        
        if not payloads:
            return {"errors": state.get("errors", []) + ["Transmission skipped: No vector payloads to send."]}
            
        import json
        from mcp import ClientSession
        from mcp.client.http import HttpClient
        
        try:
            # Connect to our decoupled MCP server running on localhost or a cloud container
            # Using the streamable-http transport endpoint matching our Step 5 server
            async with HttpClient("http://localhost:8000") as client:
                # Initialize an active protocol session with the server
                async with ClientSession(client.incoming, client.outgoing) as session:
                    await session.initialize()
                    
                    # Convert our verified Pydantic-mapped payloads into a serialized string
                    payload_string = json.dumps(payloads)
                    
                    logger.info("mcp_client_calling_remote_tool", total_records=len(payloads))
                    
                    # Execute the universal tool call exposed by our storage service
                    result = await session.call_tool(
                        "write_to_s3_vector_bucket", 
                        arguments={"payloads_json": payload_string}
                    )
                    
                    # Log out the server response confirmation text
                    logger.info("mcp_server_response_received", response=result.content)
                    
            return {"errors": state.get("errors", [])} # Clean transmission exit
            
        except Exception as e:
            logger.error("mcp_client_transmission_failed", error=str(e))
            # If the cloud connection blips, we add it to errors so our router can catch it
            return {"errors": state.get("errors", []) + [f"MCP Transmission Error: {str(e)}"]}

# Example verification test execution
if __name__ == "__main__":
    print("--- Testing LangGraph Node Functionality ---")
    nodes = RAGIngestionNodes()
    
    # Setup mock initial graph state
    initial_state = AgentState(
        raw_file_bytes=b"This is a test document to verify our state machine nodes execute flawlessly.",
        file_type="txt",
        text_chunks=[],
        vector_payloads=[],
        errors=[]
    )
    
    # Simulate routing through the state updates
    state_update_1 = nodes.parse_and_chunk_node(initial_state)
    initial_state.update(state_update_1)
    
    state_update_2 = nodes.generate_embeddings_node(initial_state)
    initial_state.update(state_update_2)
    
    print(f"Successfully processed chunks: {len(initial_state['text_chunks'])}")
    print(f"Generated Vector Payloads: {len(initial_state['vector_payloads'])}")
    if initial_state['vector_payloads']:
        print(f"Vector Dimensions Check: {len(initial_state['vector_payloads'][0]['vector'])} dimensions")