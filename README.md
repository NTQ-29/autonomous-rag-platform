### **autonomous-rag-platform

### Autonomous Cloud-Native RAG Platform

An enterprise-grade, asynchronous, and self-healing Retrieval-Augmented Generation (RAG) document ingestion engine. This platform decouples high-latency document parsing, chunking, and vector embedding generation from core application logic using a stateful agent topology and the **Model Context Protocol (MCP)**. 

Designed specifically to bypass local machine compute constraints, the architecture leverages serverless cloud patterns to process massive document datasets cheaply, securely, and at scale.

---

#### Architectural Topology

The platform is designed around strict decoupling, event-driven transitions, and fallback capability:

1. **Orchestration Layer (LangGraph):** Manages the processing lifecycle as a deterministic state machine. It handles raw data ingestion, enforces token-aware chunk boundaries, generates vector embeddings, and utilizes a validation routing engine to autonomously heal from file-parsing failures.
2. **Abstraction Layer (Model Context Protocol):** Exposes downstream cloud infrastructure to the agent graph via a standardized `FastMCP` server over a streamable network interface.
3. **Storage Layer (AWS Data Lake):** Persists raw materials inside a secure document landing zone, while utilizing high-dimensional coordinate mapping natively within an **Amazon S3 Vector Bucket** for sub-second, cost-effective similarity queries.

---

#### Repository Ecosystem

* `mcp_server.py` - Standardized FastMCP Server exposing AWS S3 infrastructure interfaces as pluggable agent tools.
* `app.py` - Compiles the `StateGraph` configuration, establishes conditional validation edges, and runs the streaming runtime.
* `graph_nodes.py` - Discrete state-mutating execution steps for parsing text, handling token window operations, and generating OpenAI/Bedrock embeddings.
* `ingestor.py` - Highly decoupled parser engine processing text from PDFs, DOCX, and Markdown files asynchronously.
* `schemas.py` - Strict Pydantic models validating data boundaries before network transmission.
* `main.tf` - Declarative Infrastructure-as-Code blueprint deploying isolated S3 buckets, S3 Vector indexes, and tight IAM least-privilege security permissions.
* `Dockerfile` - Light, immutable containerization wrapper enabling modular cloud container distribution.

---

### Quickstart & Local Replication

#### 1. Environment Configurations
Clone the repository and install the verified dependency tree:
```bash
pip install -r requirements.txt
