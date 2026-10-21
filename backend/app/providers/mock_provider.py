from typing import List, Dict, Any, Optional, Type
from pydantic import BaseModel
from backend.app.providers.base import (
    LLMProvider,
    ProviderResult,
    ProviderStructuredResult,
    ProviderToolResult,
    TokenUsage,
    ToolCallRequest
)
from backend.app.schemas.evaluation import LLMEvaluationResponse, RubricCheckpointResult

class MockProvider(LLMProvider):
    """
    Deterministic offline provider for unit, graph, and CI testing.
    Does not require an API key or internet access.
    Can be configured to simulate passes, specific checkpoint failures, or tool calls.
    """

    def __init__(
        self,
        canned_lesson: Optional[str] = None,
        simulate_eval_pass: bool = True,
        simulate_eval_failures: Optional[List[str]] = None,
        tool_call_query: Optional[str] = "RAG core concepts"
    ):
        self.canned_lesson = canned_lesson or (
            "# Introduction to RAG (Retrieval-Augmented Generation)\n\n"
            "Imagine you are preparing for your college semester exams in India. "
            "You have studied well, but you cannot remember every single college rule or fee deadline. "
            "Instead of guessing, you open your college handbook, search for the exact rule, read it, and answer your friend's question. "
            "This is exactly how Retrieval-Augmented Generation (RAG) works in Artificial Intelligence!\n\n"
            "## 1. What is RAG?\n"
            "Retrieval-Augmented Generation (RAG) is an AI method that combines two parts [REF-01]:\n"
            "1. **Retrieval**: Finding relevant facts from an external document library.\n"
            "2. **Augmentation & Generation**: Providing those retrieved facts to a language model so it can generate grounded, helpful answers and reduce unsupported guesses.\n\n"
            "A Large Language Model (LLM) relies on knowledge learned during training, as well as context provided in the current prompt. "
            "With RAG, the system looks up external or updated documents at question time and supplies them directly in the prompt [REF-03].\n\n"
            "## 2. Why Does RAG Matter?\n"
            "1. **Accurate Facts**: It helps prevent the AI from making up false answers (called hallucinations).\n"
            "2. **Private Data Access**: A company or college can let students ask questions about internal policy circulars without retraining the model.\n"
            "3. **Cost Savings**: Training a large language model from scratch can be expensive and resource-intensive. With RAG, organizations can add or update external documents without having to retrain the underlying model for every change.\n\n"
            "## 3. How RAG Works Step-by-Step\n"
            "1. **Chunking**: Long documents are cut into smaller, bite-sized sections called text chunks [REF-02].\n"
            "2. **Embeddings**: An embedding is a list of numbers representing the meaning of a text chunk, like a digital barcode [REF-02].\n"
            "3. **Retrieval**: When you ask a question, the computer compares the question's barcode with document barcodes and picks the best matching chunks.\n"
            "4. **Generation**: The retrieved chunks are pasted into the model's prompt as context, and the model writes the final response.\n\n"
            "## 4. Concrete Worked Example: College Library Assistant\n\n"
            "> **Note:** The following college library assistant scenario is a fictional illustrative example used solely to explain RAG ingestion, retrieval, and generation steps.\n\n"
            "Let us walk through a practical example from an Indian college:\n"
            "- **User Question**: 'What is the penalty for returning a library book 3 days late?'\n"
            "- **Without RAG**: The AI might guess: 'The fee is 50 rupees,' which could be wrong.\n"
            "- **Step 1 (Retrieve)**: The RAG system searches the college library manual and finds Rule 4.2: 'A late fee of 5 rupees per day applies for the first week.'\n"
            "- **Step 2 (Generate)**: The AI reads Rule 4.2 and answers: 'According to Rule 4.2 of your college manual, returning a book 3 days late costs 15 rupees (5 rupees per day).'\n\n"
            "## 5. Limitations and Misunderstandings\n"
            "- **Misunderstanding**: Does RAG retrain the model weights every time it retrieves a document? **No!** Retrieval happens at inference time and does not modify the model's neural network weights [REF-01].\n"
            "- **Limitation**: RAG reduces errors, but cannot guarantee 100% correctness [REF-04]. If the search engine retrieves the wrong rule, the generated answer will also be wrong.\n\n"
            "## 6. Key Takeaways\n"
            "- RAG stands for Retrieval-Augmented Generation [REF-01].\n"
            "- It searches external documents to help ground answers in real evidence without retraining weights [REF-01].\n"
            "- Documents are split into chunks and indexed with numerical embeddings [REF-02].\n"
            "- Quality depends on retrieving the right context before generating the answer [REF-04].\n\n"
            "## 7. References and Source Grounding\n\n"
            "| Reference ID | Title | Authors / Source | Grounded Topics | URL |\n"
            "|---|---|---|---|---|\n"
            "| **[REF-01]** | Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks | Patrick Lewis, Ethan Perez, Aleksandra Piktus, et al. (2020) | Parametric vs. non-parametric memory; inference-only retrieval; no weight retraining | [https://arxiv.org/abs/2005.11401](https://arxiv.org/abs/2005.11401) |\n"
            "| **[REF-02]** | LlamaIndex Documentation: High-Level Concepts (Chunking, Embeddings, Retrieval) | LlamaIndex Documentation | Chunking strategies, vector embeddings, similarity search | [https://docs.llamaindex.ai/en/stable/getting_started/concepts/](https://docs.llamaindex.ai/en/stable/getting_started/concepts/) |\n"
            "| **[REF-03]** | LangChain Documentation: Retrieval-Augmented Generation (RAG) Architecture | Harrison Chase, LangChain Team | Ingestion and retrieval pipelines, context injection, college handbook query | [https://python.langchain.com/docs/tutorials/rag/](https://python.langchain.com/docs/tutorials/rag/) |\n"
            "| **[REF-04]** | Anthropic Documentation: Prompt Engineering Overview | Anthropic Documentation | Prompt grounding, evidence constraints, hallucination reduction | [https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview) |\n"
        )
        self.simulate_eval_pass = simulate_eval_pass
        self.simulate_eval_failures = simulate_eval_failures or []
        self.tool_call_query = tool_call_query
        self.calls_count = 0

    def generate_text(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 3000
    ) -> ProviderResult:
        self.calls_count += 1
        return ProviderResult(
            content=self.canned_lesson,
            token_usage=TokenUsage(prompt_tokens=250, completion_tokens=550, total_tokens=800),
            latency_ms=45.0,
            model="mock/offline-engine"
        )

    def generate_structured(
        self,
        messages: List[Dict[str, str]],
        schema: Type[BaseModel],
        model: Optional[str] = None,
        temperature: float = 0.1
    ) -> ProviderStructuredResult:
        self.calls_count += 1
        from backend.app.schemas.evaluation import MANDATORY_CHECKPOINT_IDS

        checkpoints = []
        for cid in MANDATORY_CHECKPOINT_IDS:
            if cid in self.simulate_eval_failures or not self.simulate_eval_pass:
                checkpoints.append(
                    RubricCheckpointResult(
                        checkpoint_id=cid,
                        passed=False,
                        evidence=f"Mock failure evidence for {cid}",
                        failure_reason=f"Failed simulated criteria on {cid}",
                        correction_instruction=f"Revise and clarify {cid}",
                        evidence_span=f"Simulated draft excerpt for {cid}"
                    )
                )
            else:
                checkpoints.append(
                    RubricCheckpointResult(
                        checkpoint_id=cid,
                        passed=True,
                        evidence=f"Verified grounded evidence for {cid}"
                    )
                )

        eval_resp = LLMEvaluationResponse(
            checkpoints=checkpoints,
            evaluator_summary="Mock evaluation result"
        )

        return ProviderStructuredResult(
            parsed=eval_resp,
            raw_content=eval_resp.model_dump_json(),
            token_usage=TokenUsage(prompt_tokens=400, completion_tokens=200, total_tokens=600),
            latency_ms=30.0,
            model="mock/offline-judge"
        )

    def call_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.5
    ) -> ProviderToolResult:
        self.calls_count += 1
        if self.tool_call_query:
            tc = ToolCallRequest(
                call_id="mock-call-1",
                function_name="search_reference_pack",
                arguments={"query": self.tool_call_query, "max_results": 3}
            )
            return ProviderToolResult(
                content=None,
                tool_calls=[tc],
                token_usage=TokenUsage(prompt_tokens=150, completion_tokens=30, total_tokens=180),
                latency_ms=25.0,
                model="mock/offline-tool"
            )
        return ProviderToolResult(
            content="No tools needed.",
            tool_calls=[],
            token_usage=TokenUsage(prompt_tokens=150, completion_tokens=10, total_tokens=160),
            latency_ms=20.0,
            model="mock/offline-tool"
        )
