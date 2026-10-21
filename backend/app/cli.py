import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.graph.workflow import run_lesson_workflow
from backend.app.providers.groq_provider import GroqProvider
from backend.app.providers.mock_provider import MockProvider
from backend.app.core.config import settings
from backend.app.core.logging import logger

def main():
    parser = argparse.ArgumentParser(description="Agentic Content Evaluator — Self-Evaluating Lesson Pipeline")
    parser.add_argument("--topic", type=str, default="Introduction to RAG", help="Lesson topic")
    parser.add_argument("--demo-error", action="store_true", help="Inject deliberate false claim to test evaluator detection and recovery")
    parser.add_argument("--offline", action="store_true", help="Run with mock provider without Groq API calls")
    parser.add_argument("--export-artifacts", action="store_true", default=True, help="Save approved lesson and rejection log to artifacts/")

    args = parser.parse_args()

    if args.offline or not settings.GROQ_API_KEY:
        logger.info("Running in OFFLINE mode using MockProvider.")
        provider = MockProvider()
    else:
        logger.info(f"Running in LIVE mode using GroqProvider (Model: {settings.GROQ_MODEL}).")
        provider = GroqProvider()

    final_state = run_lesson_workflow(
        topic=args.topic,
        enable_deliberate_error=args.demo_error,
        provider=provider,
        max_retries=settings.MAX_RETRIES
    )

    print("\n" + "=" * 60)
    print(f"RUN RESULT: {final_state['status']}")
    print(f"Run ID: {final_state['run_id']}")
    print(f"Attempts Made: {final_state['attempt_number']}")
    print(f"Rejection Logs Recorded: {len(final_state['rejection_log'])}")
    print("=" * 60 + "\n")

    if args.export_artifacts:
        artifacts_dir = Path(__file__).resolve().parent.parent.parent / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Export Rejection Logs
        rejection_json_path = artifacts_dir / "rejection_log.json"
        with open(rejection_json_path, "w", encoding="utf-8") as f:
            json.dump(final_state["rejection_log"], f, indent=2)

        rejection_md_path = artifacts_dir / "rejection_log.md"
        with open(rejection_md_path, "w", encoding="utf-8") as f:
            f.write(f"# Rejection Log: {final_state['topic']}\n\n")
            f.write(f"- **Run ID**: `{final_state['run_id']}`\n")
            f.write(f"- **Final Status**: `{final_state['status']}`\n")
            f.write(f"- **Total Attempts**: {final_state['attempt_number']}\n\n")
            if not final_state["rejection_log"]:
                f.write("No rejections recorded. Lesson passed all checks on the initial attempt.\n")
            else:
                for r in final_state["rejection_log"]:
                    f.write(f"## Attempt {r['attempt_number']} Rejection\n")
                    f.write(f"- **Timestamp**: {r['timestamp']}\n")
                    f.write(f"- **Failed Checkpoints**: {', '.join(r['failed_checkpoints'])}\n")
                    f.write("### Failure Reasons:\n")
                    for reas in r["reasons"]:
                        f.write(f"- {reas}\n")
                    f.write("### Corrective Instructions Sent to Generator:\n")
                    for ci in r["corrective_instructions"]:
                        f.write(f"- {ci}\n")
                    f.write(f"### Changes Required:\n```\n{r['changes_required']}\n```\n")
                    if r.get("actual_changes_made"):
                        f.write(f"### Actual Changes Made on Regeneration (Attempt {r['attempt_number'] + 1}):\n")
                        f.write(f"{r['actual_changes_made']}\n\n")

        # Export Approved Lesson ONLY if passed
        if final_state["status"] == "PASSED" and final_state["final_approved_lesson"]:
            lesson_md_path = artifacts_dir / "lesson.md"
            with open(lesson_md_path, "w", encoding="utf-8") as f:
                f.write(final_state["final_approved_lesson"])
            print(f"Approved lesson saved to: {lesson_md_path}")
        else:
            print("Notice: Lesson did not pass; no approved lesson exported to artifacts/lesson.md.")

        print(f"Rejection logs saved to: {rejection_json_path} and {rejection_md_path}")

if __name__ == "__main__":
    main()
