from pydantic import BaseModel
from typing import Literal

class Profile(BaseModel):
    name: str
    gender: str
    profile_id: str

class Report(BaseModel):
    category: Literal["健康风险", "遗传特征", "遗传性疾病", "营养代谢", "药物指南", "运动基因", "皮肤特性", "心理特质"]
    report_id: str
    report_name: str
    report_gender_category: Literal["全部", "男", "女"]
    report_endpoint: str
    sample_result: str | None = None