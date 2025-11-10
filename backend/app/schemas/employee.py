"""
Employee Schemas
"""
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import date, datetime


class EmployeeBase(BaseModel):
    """Base employee schema"""
    full_name_kanji: str
    full_name_kana: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    zairyu_card_number: Optional[str] = None
    zairyu_expire_date: Optional[date] = None
    address: Optional[str] = None
    current_address: Optional[str] = None  # 現住所 - Base address
    address_banchi: Optional[str] = None  # 番地 - Block/lot number
    address_building: Optional[str] = None  # 物件名 - Building name
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None


class EmployeeCreate(EmployeeBase):
    """Create employee from candidate"""
    rirekisho_id: str  # Changed from uns_id
    factory_id: str
    hakensaki_shain_id: Optional[str] = None
    hire_date: date
    jikyu: int
    position: Optional[str] = None
    contract_type: Optional[str] = None
    apartment_id: Optional[int] = None
    apartment_start_date: Optional[date] = None
    apartment_rent: Optional[int] = None
    is_corporate_housing: bool = False  # 社宅 (Corporate Housing)


class EmployeeUpdate(BaseModel):
    """Update employee"""
    full_name_kanji: Optional[str] = None
    full_name_kana: Optional[str] = None
    factory_id: Optional[str] = None
    hakensaki_shain_id: Optional[str] = None
    jikyu: Optional[int] = None
    position: Optional[str] = None
    address: Optional[str] = None
    current_address: Optional[str] = None  # 現住所 - Base address
    address_banchi: Optional[str] = None  # 番地 - Block/lot number
    address_building: Optional[str] = None  # 物件名 - Building name
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    apartment_id: Optional[int] = None
    apartment_rent: Optional[int] = None
    is_corporate_housing: bool = False  # 社宅 (Corporate Housing)
    zairyu_expire_date: Optional[date] = None


class EmployeeResponse(EmployeeBase):
    """Employee response"""
    id: int
    hakenmoto_id: int
    rirekisho_id: Optional[str]  # Changed from uns_id
    factory_id: Optional[str]
    factory_name: Optional[str] = None  # Nombre de la fábrica
    hakensaki_shain_id: Optional[str]  # 派遣先ID - ID que la fábrica asigna al empleado
    hire_date: Optional[date]  # 入社日
    current_hire_date: Optional[date]  # 現入社 - Fecha de entrada a fábrica actual
    jikyu: int  # 時給
    jikyu_revision_date: Optional[date]  # 時給改定
    photo_url: Optional[str] = None  # Added photo
    photo_data_url: Optional[str] = None  # Base64 encoded photo data
    position: Optional[str]
    contract_type: Optional[str]
    current_address: Optional[str] = None  # 現住所 - Base address
    address_banchi: Optional[str] = None  # 番地 - Block/lot number
    address_building: Optional[str] = None  # 物件名 - Building name

    # Assignment information
    assignment_location: Optional[str]  # 配属先
    assignment_line: Optional[str]  # 配属ライン
    job_description: Optional[str]  # 仕事内容

    # Financial
    hourly_rate_charged: Optional[int]  # 請求単価
    billing_revision_date: Optional[date]  # 請求改定
    profit_difference: Optional[int]  # 差額利益
    standard_compensation: Optional[int]  # 標準報酬
    health_insurance: Optional[int]  # 健康保険
    nursing_insurance: Optional[int]  # 介護保険
    pension_insurance: Optional[int]  # 厚生年金
    social_insurance_date: Optional[date]  # 社保加入日

    # Visa and documents
    visa_type: Optional[str]  # ビザ種類
    visa_renewal_alert: Optional[bool]  # ビザ更新アラート
    visa_alert_days: Optional[int]  # アラート日数
    license_type: Optional[str]  # 免許種類
    license_expire_date: Optional[date]  # 免許期限
    commute_method: Optional[str]  # 通勤方法
    optional_insurance_expire: Optional[date]  # 任意保険期限
    japanese_level: Optional[str]  # 日本語検定
    career_up_5years: Optional[bool]  # キャリアアップ5年目
    entry_request_date: Optional[date]  # 入社依頼日
    notes: Optional[str]  # 備考
    postal_code: Optional[str]  # 〒

    # Apartment
    apartment_id: Optional[int]  # アパートID
    apartment_start_date: Optional[date]  # 入居日
    apartment_move_out_date: Optional[date]  # 退去日
    apartment_rent: Optional[int]
    is_corporate_housing: bool = False  # 社宅 (Corporate Housing)

    # Yukyu (paid vacation)
    yukyu_total: int
    yukyu_used: int
    yukyu_remaining: int

    # Status
    current_status: Optional[str]  # 現在: active, terminated, suspended
    is_active: bool
    termination_date: Optional[date]  # 退社日
    termination_reason: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class EmployeeTerminate(BaseModel):
    """Terminate employee"""
    termination_date: date
    termination_reason: str


class YukyuUpdate(BaseModel):
    """Update yukyu balance"""
    yukyu_total: int
    notes: Optional[str] = None
