from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal

OpType = Literal['opening_balance','intake','withdrawal','issue_for_control','movement','adjustment']

class OperationCreate(BaseModel):
    date: str = Field(..., description="Дата операции YYYY-MM-DD")
    period_month: str = Field(..., description="Период YYYY-MM")
    op_type: OpType = Field(..., description="Тип операции")
    species_code: str = Field(..., description="Код вида")
    direction_code: Literal['subsidiary','vivarium'] = Field(..., description="Направление")
    quantity: int = Field(..., description="Количество; для adjustment может быть отрицательным/положительным")

    sex: Optional[str] = Field(None, description="M/F/U")
    age_bin_code: Optional[str] = Field(None, description="Код возрастной категории")
    mass_bin_code: Optional[str] = Field(None, description="Код весовой категории")

    group_code: Optional[str] = Field(None, description="Код группы")
    cohort_code: Optional[str] = Field(None, description="Код когорты")

    src_group_code: Optional[str] = Field(None, description="Источник: группа")
    src_cohort_code: Optional[str] = Field(None, description="Источник: когорта")
    dst_group_code: Optional[str] = Field(None, description="Приемник: группа")
    dst_cohort_code: Optional[str] = Field(None, description="Приемник: когорта")
    transfer_key: Optional[str] = Field(None, description="Ключ перемещения")

    purpose_text: Optional[str] = Field(None, description="Для issue_for_control")
    reason: Optional[str] = Field(None, description="Причина для adjustment")
    adjusts_period: Optional[str] = Field(None, description="Корректируемый период YYYY-MM")

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v, info):
        op_type = info.data.get("op_type")
        if op_type == "adjustment":
            if v == 0:
                raise ValueError("quantity не может быть 0 для корректировки")
        else:
            if v <= 0:
                raise ValueError("quantity должен быть > 0")
        return v
