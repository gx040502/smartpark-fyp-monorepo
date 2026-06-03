/**
 * Next.js API Route — /api/chat
 *
 * Proxies chat messages from the frontend (useChat) to the
 * Python FastAPI AI service, which handles LLM inference and
 * SQL execution via the Laravel backend.
 */

const PYTHON_AI_SERVICE_URL =
  process.env.PYTHON_AI_SERVICE_URL || "http://localhost:8001"

export async function POST(req: Request) {
  const body = await req.json() // body = {messages: [...]}  

  try {
    // Forward the messages to the Python AI service
    const response = await fetch(`${PYTHON_AI_SERVICE_URL}/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        messages: body.messages,
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error("Python AI service error:", response.status, errorText)

      // Return a streaming error message
      return createErrorStream(
        `AI service error (${response.status}): ${errorText}`
      )
    }

    // Stream the response directly from Python → Browser
    return new Response(response.body, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "X-Vercel-AI-Data-Stream": "v1",
      },
    })
  } catch (error) {
    console.error("Failed to connect to Python AI service:", error)

    return createErrorStream(
      "Cannot connect to the AI service. Please make sure the Python FastAPI server is running on port 8001. " +
      "Start it with: cd ai-service && uvicorn main:app --port 8001"
    )
  }
}

/**
 * Creates a streaming error response in the AI SDK data stream format
 * so the chat UI can display the error message naturally.
 */
function createErrorStream(errorMessage: string): Response {
  const encoder = new TextEncoder()
  const words = errorMessage.split(" ")

  const stream = new ReadableStream({
    async start(controller) {
      for (const word of words) {
        controller.enqueue(
          encoder.encode(`0:${JSON.stringify(word + " ")}\n`)
        )
        await new Promise((r) => setTimeout(r, 30))
      }
      controller.enqueue(
        encoder.encode(
          `d:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n`
        )
      )
      controller.close()
    },
  })

  return new Response(stream, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "X-Vercel-AI-Data-Stream": "v1",
    },
  })
}
