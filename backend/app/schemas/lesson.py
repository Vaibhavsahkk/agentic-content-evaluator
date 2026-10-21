from typing import List, Optional
from pydantic import BaseModel, Field

class LessonSection(BaseModel):
    section_title: str = Field(description="Title of the section")
    content: str = Field(description="Body of the section in plain beginner-friendly English")
    grounded_reference_ids: List[str] = Field(default_factory=list, description="IDs of references backing this section (e.g. REF-01)")

class LessonDraft(BaseModel):
    title: str = Field(description="Lesson title")
    target_audience: str = Field(description="Target learner persona")
    summary: str = Field(description="Brief 2-3 sentence overview")
    sections: List[LessonSection] = Field(description="Ordered lesson sections")
    worked_example: str = Field(description="Concrete relatable worked example (e.g., college handbook policy)")
    key_takeaways: List[str] = Field(description="Bullet point takeaways")
    references_cited: List[str] = Field(default_factory=list, description="All reference IDs cited in the lesson")
    markdown_content: str = Field(description="Complete standalone formatted Markdown representation")

    def get_full_text(self) -> str:
        """Returns the full text used for deterministic and LLM evaluation."""
        if self.markdown_content and len(self.markdown_content.strip()) > 50:
            return self.markdown_content
        parts = [f"# {self.title}\n", self.summary, "\n"]
        for s in self.sections:
            parts.append(f"## {s.section_title}\n{s.content}\n")
        parts.append(f"## Concrete Example\n{self.worked_example}\n")
        parts.append("## Key Takeaways\n" + "\n".join(f"- {k}" for k in self.key_takeaways))
        return "\n".join(parts)
