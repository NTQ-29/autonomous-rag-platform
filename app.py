from langgraph.graph import StateGraph, END
import structlog
from graph_nodes import AgentState, RAGIngestionNodes

logger = structlog.get_logger()

# Define the routing logic function
def validation_router(state: AgentState) -> str:
    """
    Inspects the state after steps execute to decide the next path.
    Returns the string name of the next node to execute.
    """
    errors = state.get("errors", [])
    
    # If errors exist and we haven't tried fixing them yet, route to self-correction
    if errors and not any("Recovered" in err for err in errors):
        logger.info("router_decision_error_detected", routing_to="autonomous_fix")
        return "autonomous_fix"
        
    # If errors are unrecoverable, halt the system gracefully
    if errors and any("Unrecoverable" in err for err in errors):
        logger.error("router_decision_halt", routing_to=END)
        return END

    # No major errors? Proceed cleanly to the end or next step
    logger.info("router_decision_healthy", routing_to=END)
    return END

def build_autonomous_ingestion_graph():
    builder = StateGraph(AgentState)
    nodes = RAGIngestionNodes()
    
    # Register all 4 structural nodes
    builder.add_node("parse_and_chunk", nodes.parse_and_chunk_node)
    builder.add_node("generate_embeddings", nodes.generate_embeddings_node)
    builder.add_node("autonomous_fix", nodes.autonomous_fix_node)
    builder.add_node("transmit_to_cloud", nodes.transmit_to_cloud_node) # <-- New
    
    # Define Entry Point and initial linear step
    builder.set_entry_point("parse_and_chunk")
    builder.add_edge("parse_and_chunk", "generate_embeddings")
    
    # Update the validation router logic mapping:
    # Instead of pointing healthy runs to END, point them to our transmission tool node!
    builder.add_conditional_edges(
        "generate_embeddings",
        validation_router, # (Make sure your validation_router returns "transmit_to_cloud" instead of END for healthy paths!)
        {
            "autonomous_fix": "autonomous_fix",
            "transmit_to_cloud": "transmit_to_cloud"
        }
    )
    
    # Loop back out of the fix node to regenerate embeddings
    builder.add_edge("autonomous_fix", "generate_embeddings")
    
    # Once transmission to the cloud completes via the MCP client, we are officially done!
    builder.add_edge("transmit_to_cloud", END)
    
    compiled_graph = builder.compile()
    return compiled_graph

if __name__ == "__main__":
    print("--- Running Autonomous Self-Correction Graph ---")
    rag_workflow = build_autonomous_ingestion_graph()
    
    # Simulating a file payload that will trigger a parsing crash 
    # (Passing bad bytes with a 'pdf' label forces pypdf to fail)
    broken_payload = {
        "raw_file_bytes": b"Malicious or corrupted un-parsable PDF bytes string.",
        "file_type": "pdf", 
        "text_chunks": [],
        "vector_payloads": [],
        "errors": []
    }
    
    for event in rag_workflow.stream(broken_payload):
        for node_name, state_output in event.items():
            print(f"\n>> Executed Node: '{node_name}'")
            if "errors" in state_output and state_output["errors"]:
                print(f"   Current Error State: {state_output['errors']}")