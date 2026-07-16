# SmartPark Architecture: The Role of FastAPI

FastAPI acts as the bridge connecting your web applications (Next.js & Laravel) to your Python-based Artificial Intelligence models. Because AI tools like HuggingFace and YOLO run in Python, FastAPI wraps them into standard web servers so your other applications can communicate with them easily.

Here are the diagrams showing exactly how the two FastAPI services fit into your ecosystem:

## 1. AI Text-to-SQL Agent (`ai-service` on port 8001)

This FastAPI service connects your Admin Dashboard chat interface to the HuggingFace LLM and your Laravel database.

```mermaid
sequenceDiagram
    participant Admin as Next.js Dashboard
    participant FastAPI as FastAPI (ai-service)
    participant HF as HuggingFace (Qwen LLM)
    participant Laravel as Laravel Backend
    participant DB as MySQL Database

    Admin->>+FastAPI: 1. POST /generate (User asks: "How many cars?")
    FastAPI->>+HF: 2. Send prompt with database schema
    HF-->>-FastAPI: 3. Return SQL Query (e.g., SELECT COUNT(*) ...)
    
    FastAPI->>+Laravel: 4. POST /ai/query (Execute SQL)
    Laravel->>+DB: 5. Run SELECT statement
    DB-->>-Laravel: 6. Return database rows
    Laravel-->>-FastAPI: 7. Return JSON results
    
    FastAPI->>+HF: 8. Send SQL results to generate natural language answer
    HF-->>-FastAPI: 9. Return conversational answer
    FastAPI-->>-Admin: 10. Stream text response to dashboard chat
```

<br>

## 2. Traffic Impact Assessment (`traffic-congestion` on port 8002)

This FastAPI service receives configuration from your frontend, runs computer vision locally on your machine using YOLO, and alerts the backend when congestion occurs.

```mermaid
graph TD
    subgraph Frontend
        Next[Next.js Admin Dashboard]
    end

    subgraph FastAPIService [FastAPI Service]
        API[API Endpoints]
        Thread[Background Video Loop]
        YOLO[YOLOv11 & ByteTrack]
    end

    subgraph Backend
        Laravel[Laravel Webhook]
    end

    %% Flow
    Next -- "1. Uploads Video\nPOST /upload" --> API
    Next -- "2. Sends ROI Polygon Points\nPOST /roi/coordinates" --> API
    API -- "3. Starts background thread" --> Thread
    Thread -- "4. Feeds frames" --> YOLO
    YOLO -- "5. Returns bounding boxes\n& vehicle IDs" --> Thread
    Thread -- "6. Calculates dwell time\n& density in ROI" --> Thread
    
    Thread -- "7. If Congested (Webhook)\nPOST /webhooks/congestion" --> Laravel
    
    classDef fastapi fill:#059669,stroke:#047857,stroke-width:2px,color:white;
    classDef nextjs fill:#000000,stroke:#333333,stroke-width:2px,color:white;
    classDef laravel fill:#ef4444,stroke:#b91c1c,stroke-width:2px,color:white;
    classDef ai fill:#3b82f6,stroke:#2563eb,stroke-width:2px,color:white;

    class API,Thread fastapi;
    class Next nextjs;
    class Laravel laravel;
    class YOLO ai;
```

### Key Takeaways
- **Language Bridge:** Next.js uses TypeScript, Laravel uses PHP, and YOLO/HuggingFace use Python. FastAPI allows them all to talk to each other using HTTP and JSON.
- **Microservices:** By putting the AI in separate FastAPI servers, heavy tasks like video processing don't slow down your Laravel backend or your dashboard UI.
