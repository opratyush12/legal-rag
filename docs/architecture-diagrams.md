# Legal RAG — Architecture Diagrams

## 1. User Journey Map

```mermaid
journey
    title Legal RAG — User Journey Map
    section Discovery
      Open App in Browser: 5: User
      View Hero Search Page: 5: User
    section Search
      Type Legal Query: 5: User
      Query Expansion (LLM): 4: System
      FAISS Vector Search: 5: System
      CrossEncoder Reranking: 5: System
      AI Summary Generation: 4: System
      View Ranked Results: 5: User
    section Case Analysis
      Click Case Card: 5: User
      Read AI Summary + Snippet: 5: User
      Preview Full Case Text: 4: User
      Download Original PDF: 4: User
    section Case Chat
      Open Chat Panel: 5: User
      Ask Question About Case: 5: User
      Receive AI Legal Analysis: 5: System
      Multi-turn Conversation: 4: User
    section Legal Assistant
      Open Assistant Panel: 5: User
      Ask Constitutional Question: 5: User
      Get Expert Legal Answer: 5: System
    section Voice & Upload
      Listen via Text-to-Speech: 4: User
      Upload Own PDF for Search: 4: User
      View Matching Cases: 5: User
```

---

## 2. Detailed System Design & Deployment Architecture

```mermaid
graph TB
    subgraph INTERNET["🌐 Internet"]
        USER["👤 User Browser<br/>React SPA + Tailwind"]
    end

    subgraph AWS["☁️ AWS Cloud — us-east-1"]
        subgraph VPC["VPC 10.0.0.0/16"]
            subgraph ALB_LAYER["Application Load Balancer"]
                ALB["ALB<br/>Port 80 HTTP<br/>Path-based Routing"]
            end

            subgraph PUB_SUB_1["Public Subnet 10.0.1.0/24 — AZ us-east-1a"]
                subgraph ECS_BE["ECS Fargate — Backend"]
                    BE_TASK["🐍 Backend Task<br/>1 vCPU · 2 GB RAM<br/>Python 3.11 · FastAPI · Uvicorn<br/>Port 8000"]
                    subgraph BE_MODELS["ML Models in-memory"]
                        EMBED["📊 bge-small-en-v1.5<br/>384-dim Embeddings<br/>33M params"]
                        RERANK["🔄 ms-marco-MiniLM<br/>Cross-Encoder Reranker<br/>22M params"]
                        FAISS["⚡ FAISS Index<br/>301,943 vectors<br/>445 MB"]
                        META["📋 Metadata<br/>301,943 chunks<br/>314 MB"]
                    end
                end
                subgraph ECS_FE["ECS Fargate — Frontend"]
                    FE_TASK["🌐 Frontend Task<br/>0.25 vCPU · 512 MB RAM<br/>Nginx 1.27 · React SPA<br/>Port 80"]
                end
                EFS_MT1["EFS Mount Target"]
            end

            subgraph PUB_SUB_2["Public Subnet 10.0.2.0/24 — AZ us-east-1b"]
                EFS_MT2["EFS Mount Target"]
            end
        end

        subgraph AWS_SERVICES["AWS Managed Services"]
            ECR["📦 ECR<br/>2 Repos<br/>backend + frontend<br/>Keep last 5 images"]
            S3["🪣 S3 Bucket<br/>Index Store 1.35 GB<br/>faiss.index · metadata.pkl<br/>bm25.pkl · indexed_pdfs<br/>AES-256 Encrypted"]
            SECRETS["🔐 Secrets Manager<br/>GROQ_API_KEY"]
            CW["📊 CloudWatch Logs<br/>14-day retention"]
            EFS["💾 EFS<br/>Encrypted at rest<br/>Reserved for future"]
        end

        subgraph IAM["🔑 IAM Roles"]
            EXEC_ROLE["Execution Role<br/>ECR Pull · Logs Write<br/>Secrets Read"]
            TASK_ROLE["Task Role<br/>S3 GetObject · HeadObject<br/>S3 ListBucket"]
            GH_ROLE["GitHub Actions Role<br/>OIDC Federation<br/>ECR Push · ECS Deploy"]
        end
    end

    subgraph EXTERNAL["🔗 External Services"]
        GROQ["🤖 Groq Cloud API<br/>llama-3.3-70b-versatile<br/>Query Expansion<br/>AI Summaries · Chat"]
        EDGE_TTS["🔊 Microsoft Edge TTS<br/>Neural Voices<br/>Hindi + English"]
        GITHUB["🐙 GitHub<br/>opratyush12/legal-rag<br/>CI/CD via Actions"]
    end

    USER -->|"HTTP :80"| ALB
    ALB -->|"/api/* · /health"| BE_TASK
    ALB -->|"/* default"| FE_TASK

    BE_TASK -->|"Download index at startup"| S3
    BE_TASK -->|"LLM API calls"| GROQ
    BE_TASK -->|"TTS synthesis"| EDGE_TTS
    BE_TASK --- BE_MODELS

    SECRETS -->|"Inject env var"| BE_TASK
    EXEC_ROLE -.->|"attached"| BE_TASK
    EXEC_ROLE -.->|"attached"| FE_TASK
    TASK_ROLE -.->|"attached"| BE_TASK

    ECR -->|"Pull images"| BE_TASK
    ECR -->|"Pull images"| FE_TASK

    BE_TASK -->|"Write logs"| CW
    FE_TASK -->|"Write logs"| CW

    EFS --- EFS_MT1
    EFS --- EFS_MT2

    GITHUB -->|"OIDC"| GH_ROLE
    GH_ROLE -->|"Push images"| ECR
    GH_ROLE -->|"Update service"| ECS_BE

    classDef aws fill:#FF9900,stroke:#232F3E,color:#232F3E,stroke-width:2px
    classDef fargate fill:#3B48CC,stroke:#232F3E,color:white,stroke-width:2px
    classDef external fill:#4CAF50,stroke:#2E7D32,color:white,stroke-width:2px
    classDef model fill:#E91E63,stroke:#880E4F,color:white,stroke-width:2px
    classDef user fill:#2196F3,stroke:#0D47A1,color:white,stroke-width:2px

    class ALB,ECR,S3,SECRETS,CW,EFS,EFS_MT1,EFS_MT2 aws
    class BE_TASK,FE_TASK fargate
    class GROQ,EDGE_TTS,GITHUB external
    class EMBED,RERANK,FAISS,META model
    class USER user
```

---

## 3. Search Pipeline Flow

```mermaid
flowchart LR
    Q["🔍 User Query"] --> QE["Query Expansion<br/>Groq LLM<br/>3 legal variants"]
    QE --> FAISS_S["FAISS Search<br/>301K vectors<br/>top-200 chunks"]
    QE --> BM25["BM25 Search<br/>keyword match<br/>top-200 chunks<br/>⚠️ disabled in prod"]

    FAISS_S --> AGG["Score Aggregation<br/>per PDF<br/>semantic × 0.65<br/>+ BM25 × 0.35<br/>+ chunk boost"]
    BM25 --> AGG

    AGG --> TOP20["Top-20<br/>Candidate PDFs"]
    TOP20 --> RERANK_S["CrossEncoder<br/>Reranking<br/>ms-marco-MiniLM"]
    RERANK_S --> TOP5["Top-5<br/>Final Results"]
    TOP5 --> SUMMARY["Groq AI<br/>Relevance<br/>Summaries"]
    SUMMARY --> RESP["📄 Response<br/>to Frontend"]

    style Q fill:#2196F3,color:white
    style RESP fill:#4CAF50,color:white
    style BM25 fill:#9E9E9E,color:white
    style FAISS_S fill:#E91E63,color:white
    style RERANK_S fill:#E91E63,color:white
    style QE fill:#FF9800,color:white
    style SUMMARY fill:#FF9800,color:white
```

---

## 4. Container Startup Flow

```mermaid
flowchart TD
    START["🐳 Container Start"] --> ENTRY["entrypoint.sh"]
    ENTRY --> S3_SYNC["S3 Index Sync<br/>s3_sync_index.py"]

    S3_SYNC --> CHK_BM25{"USE_BM25?"}
    CHK_BM25 -->|"false"| SKIP_BM25["Skip bm25.pkl<br/>save 598 MB download"]
    CHK_BM25 -->|"true"| DL_BM25["Download bm25.pkl<br/>598 MB"]

    S3_SYNC --> DL_FAISS["Download faiss.index<br/>445 MB"]
    S3_SYNC --> DL_META["Download metadata.pkl<br/>314 MB"]
    S3_SYNC --> DL_CSV["Download indexed_pdfs.csv"]

    DL_FAISS --> UVICORN["Start Uvicorn<br/>port 8000"]
    DL_META --> UVICORN
    DL_CSV --> UVICORN
    SKIP_BM25 --> UVICORN
    DL_BM25 --> UVICORN

    UVICORN --> LIFESPAN["FastAPI Lifespan<br/>IndexManager.load()"]
    LIFESPAN --> LOAD_FAISS["Load FAISS Index<br/>301,943 vectors"]
    LIFESPAN --> LOAD_META["Load Metadata<br/>301,943 records"]
    LIFESPAN --> CHK_BM25_2{"USE_BM25?"}
    CHK_BM25_2 -->|"false"| SKIP2["BM25 disabled<br/>FAISS-only mode"]
    CHK_BM25_2 -->|"true"| LOAD_BM25["Load BM25<br/>~3 GB in RAM"]

    LOAD_FAISS --> READY["✅ Ready to Serve<br/>/health → 200 OK"]
    LOAD_META --> READY
    SKIP2 --> READY
    LOAD_BM25 --> READY

    READY --> MODELS["Lazy-load ML Models<br/>on first request"]
    MODELS --> EMBED_M["bge-small-en-v1.5<br/>Embedding Model"]
    MODELS --> RERANK_M["ms-marco-MiniLM<br/>Reranker Model"]

    style START fill:#3B48CC,color:white
    style READY fill:#4CAF50,color:white
    style SKIP_BM25 fill:#9E9E9E,color:white
    style SKIP2 fill:#9E9E9E,color:white
```

---

## 5. CI/CD Deployment Flow

```mermaid
flowchart LR
    DEV["👨‍💻 Developer<br/>Push to main"] --> GH["GitHub<br/>Actions"]

    GH --> OIDC["OIDC Auth<br/>AssumeRoleWithWebIdentity"]
    OIDC --> AWS_ROLE["AWS IAM Role<br/>github-actions"]

    GH --> BUILD_BE["Docker Build<br/>Backend Image"]
    GH --> BUILD_FE["Docker Build<br/>Frontend Image"]

    BUILD_BE --> PUSH_BE["Push to ECR<br/>legal-rag-backend"]
    BUILD_FE --> PUSH_FE["Push to ECR<br/>legal-rag-frontend"]

    PUSH_BE --> UPDATE["ECS Update Service<br/>force-new-deployment"]
    PUSH_FE --> UPDATE

    UPDATE --> DRAIN["Drain Old Task<br/>deregistration 30s"]
    DRAIN --> NEW_TASK["New Task<br/>Pulls image from ECR"]
    NEW_TASK --> S3_DL["Download Index<br/>from S3 ~15s"]
    S3_DL --> HEALTH["Health Check<br/>ALB + ECS"]
    HEALTH --> LIVE["✅ Live<br/>Traffic shifted"]

    style DEV fill:#2196F3,color:white
    style LIVE fill:#4CAF50,color:white
    style GH fill:#24292E,color:white
    style AWS_ROLE fill:#FF9900,color:black
```
ECS Fargate — Backend

HTTP :80

/api/* · /health

/* (default)

Download index
at startup

LLM API calls

TTS synthesis

Inject env var

attached

attached

attached

Pull images

Pull images

Write logs

Write logs

OIDC

Push images

Update service

ML Models (in-memory)

📊 bge-small-en-v1.5
384-dim Embeddings
33M params

🔄 ms-marco-MiniLM
Cross-Encoder Reranker
22M params

⚡ FAISS Index
301,943 vectors
445 MB

📋 Metadata
301,943 chunks
314 MB

👤 User Browser
React SPA + Tailwind

ALB
Port 80 HTTP
Path-based Routing

🐍 Backend Task
1 vCPU · 2 GB RAM
Python 3.11 · FastAPI · Uvicorn
Port 8000

🌐 Frontend Task
0.25 vCPU · 512 MB RAM
Nginx 1.27 · React SPA
Port 80

EFS Mount Target

ECS Fargate — Frontend




