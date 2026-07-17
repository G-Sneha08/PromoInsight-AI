import os
import json
import re
from typing import List, Optional
from pydantic import ValidationError

from src.models import QueryPlan
from src.schema_context import SchemaContext
from src.config import GEMINI_API_KEY, OPENAI_API_KEY

class LLMQueryPlanner:
    def __init__(self):
        self.context_str = SchemaContext.get_prompt_context_string()
        
    def is_configured(self) -> bool:
        return bool(GEMINI_API_KEY or OPENAI_API_KEY)
        
    def plan(self, question: str, history: Optional[List[QueryPlan]] = None) -> Optional[QueryPlan]:
        if not self.is_configured():
            return None
            
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(question, history)
        
        raw_response = ""
        try:
            if GEMINI_API_KEY:
                raw_response = self._call_gemini(system_prompt, user_prompt)
            elif OPENAI_API_KEY:
                raw_response = self._call_openai(system_prompt, user_prompt)
                
            plan = self._parse_json_to_plan(raw_response)
            return plan
        except Exception as e:
            print(f"LLM planner failed: {e}. Trying self-correction...")
            # Self correction step
            try:
                corrected_prompt = f"{user_prompt}\n\nERROR IN PREVIOUS ATTEMPT:\n{raw_response}\n\nError details: {e}\n\nPlease output the valid JSON conforming strictly to the Pydantic schema."
                if GEMINI_API_KEY:
                    raw_response = self._call_gemini(system_prompt, corrected_prompt)
                elif OPENAI_API_KEY:
                    raw_response = self._call_openai(system_prompt, corrected_prompt)
                return self._parse_json_to_plan(raw_response)
            except Exception as retry_e:
                print(f"LLM planner retry failed: {retry_e}. Falling back to Rule-Based Parser.")
                return None

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> str:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=system_prompt)
        response = model.generate_content(
            user_prompt,
            generation_config=genai.types.GenerationConfig(temperature=0.1)
        )
        return response.text

    def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1
        )
        return response.choices[0].message.content

    def _parse_json_to_plan(self, text: str) -> QueryPlan:
        # Extract JSON from markdown block if present
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Fallback to look for curly braces
            braces_match = re.search(r'(\{.*\})', text, re.DOTALL)
            if braces_match:
                json_str = braces_match.group(1)
            else:
                json_str = text
                
        data = json.loads(json_str)
        return QueryPlan(**data)

    def _build_system_prompt(self) -> str:
        return f"""You are a senior AI solutions architect and data analyst for a beverages company.
Your role is to act as a structured Query Planner. You convert natural language questions about beverage sales, inventory, and promotions into a structured analytical QueryPlan JSON.

You must conform STRICTLY to the following Pydantic QueryPlan schema:

QueryPlan:
- operations: List of OperationPlan
- needs_clarification: bool (set to true if user question is highly ambiguous)
- clarification_question: Optional string (question to ask user if needs_clarification is True)
- assumptions: List of strings (minor assumptions made to map the query)

OperationPlan:
- operation_type: one of [aggregate, compare, rank, trend, contribution, growth, promotion_uplift, inventory_status, anomaly_detection, data_quality, summary]
- metric: one of the metrics in the Metric Catalog
- dimensions: List of column names e.g. ["product_name"]
- filters: List of FilterCondition
- time_range: Optional TimeRange
- comparison: Optional ComparisonConfig
- group_by: List of columns to group by
- order_by: List of SortCondition
- limit: Optional integer (1 to 100)
- time_granularity: Optional string ("daily", "weekly", "monthly" for trends)

FilterCondition:
- field: column name e.g. "region_name"
- operator: one of [equals, not_equals, in, not_in, greater_than, greater_than_or_equal, less_than, less_than_or_equal, between, contains, is_null, is_not_null]
- value: string, number, or list of values

TimeRange:
- type: "relative" or "absolute"
- value: e.g. "last_month", "this_quarter", "latest_campaign", "previous_30_days", etc.
- start_date: YYYY-MM-DD or null
- end_date: YYYY-MM-DD or null

ComparisonConfig:
- method: "previous_non_promotional_weeks", "previous_year_period", "previous_weeks", or "none"
- number_of_weeks: integer (1 to 12)

SortCondition:
- field: column name or metric name
- direction: "ascending" or "descending"

---
{self.context_str}

CRITICAL RULES:
1. Do not invent metrics or tables. Only use what is declared in the catalogs.
2. If the user question has ambiguous elements (e.g. "best product" without metric context), set needs_clarification=true and write a clear clarification question.
3. If they ask about trends, specify time_granularity (weekly/monthly/daily) and set operation_type = "trend".
4. If they ask for follow-ups, look at the history provided. Merge prior filters or metrics.
5. Return ONLY a valid JSON block enclosed in ```json and ```. Do not add conversational text around it.
"""

    def _build_user_prompt(self, question: str, history: Optional[List[QueryPlan]]) -> str:
        prompt = []
        if history:
            prompt.append("=== CONVERSATION HISTORY ===")
            for idx, old_plan in enumerate(history[-3:]): # last 3 plans
                prompt.append(f"Turn {idx + 1} Plan: {old_plan.model_dump_json(indent=2)}")
                
        prompt.append(f"\nUser Question: \"{question}\"")
        prompt.append("\nGenerate the structured QueryPlan JSON:")
        return "\n".join(prompt)
