from pydantic import BaseModel, Field
from typing import List, Optional, Any, Union

class FilterCondition(BaseModel):
    field: str = Field(..., description="Field name in table e.g. region_name, category, product_name, etc.")
    operator: str = Field(..., description="Comparison operator: equals, not_equals, in, not_in, greater_than, greater_than_or_equal, less_than, less_than_or_equal, between, contains, is_null, is_not_null")
    value: Any = Field(None, description="Value(s) for the filter. Can be a string, list of strings/ints, number, or null.")

class TimeRange(BaseModel):
    type: str = Field(..., description="Type of time range: relative or absolute")
    value: Optional[str] = Field(None, description="Relative value name: today, yesterday, last week, this week, last month, this month, last quarter, this quarter, last year, previous 30 days, latest campaign, etc.")
    start_date: Optional[str] = Field(None, description="Start date format YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="End date format YYYY-MM-DD")

class ComparisonConfig(BaseModel):
    method: str = Field(..., description="Method for comparison: previous_non_promotional_weeks, previous_year_period, previous_weeks, or none")
    number_of_weeks: Optional[int] = Field(4, description="Number of weeks to compare (usually 1 to 12)")

class SortCondition(BaseModel):
    field: str = Field(..., description="Field name to sort by")
    direction: str = Field("descending", description="Sorting direction: ascending or descending")

class OperationPlan(BaseModel):
    operation_type: str = Field(..., description="Operation type: aggregate, compare, rank, trend, contribution, growth, promotion_uplift, inventory_status, anomaly_detection, data_quality, summary")
    metric: str = Field(..., description="Metric name to extract from metric catalog")
    dimensions: List[str] = Field(default_factory=list, description="Dimensions to project in results e.g. product_name, category, region_name, etc.")
    filters: List[FilterCondition] = Field(default_factory=list, description="Filters to apply")
    time_range: Optional[TimeRange] = Field(None, description="Date range filters")
    comparison: Optional[ComparisonConfig] = Field(None, description="Comparison context")
    group_by: List[str] = Field(default_factory=list, description="Grouping variables")
    order_by: List[SortCondition] = Field(default_factory=list, description="Order conditions")
    limit: Optional[int] = Field(None, description="Number of rows to limit")
    time_granularity: Optional[str] = Field(None, description="Trend time-bucket: daily, weekly, monthly")
    dataset_scope: Optional[str] = Field(None, description="Dataset scope for data-quality queries: overall, sales, inventory, promotions, products, regions")

class QueryPlan(BaseModel):
    operations: List[OperationPlan] = Field(default_factory=list, description="List of operations in chronological execution plan")
    needs_clarification: bool = Field(False, description="True if prompt is ambiguous and needs user input")
    clarification_question: Optional[str] = Field(None, description="A clear clarification question to ask the user")
    assumptions: List[str] = Field(default_factory=list, description="List of assumptions taken to resolve minor ambiguities")
    resolved_entity: Optional[dict] = Field(None, description="Resolved top entity from previous execution results")
