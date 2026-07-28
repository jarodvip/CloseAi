"""统一异常定义与错误处理基类"""


import uuid


class AppException(Exception):
    """应用层异常基类"""

    def __init__(self, detail: str, status_code: int = 500, trace_id: Optional[str] = None):
        self.detail = detail
        self.status_code = status_code
        self.trace_id = trace_id or str(uuid.uuid4())[:8]
        super().__init__(self.detail)

    def to_dict(self) -> dict:
        return {"code": self.status_code, "detail": self.detail, "trace_id": self.trace_id}


# 具体异常类型
class CustomerNotFound(AppException):
    def __init__(self, customer_id: int):
        super().__init__(detail=f"客户 {customer_id} 不存在", status_code=404)


class BriefingNotFound(AppException):
    def __init__(self, briefing_id: int):
        super().__init__(detail=f"简报 {briefing_id} 不存在", status_code=404)


class ChatSessionNotFound(AppException):
    def __init__(self, session_id: int):
        super().__init(detail=f"会话 {session_id} 不存在", status_code=404)


class PermissionDenied(AppException):
    def __init__(self, required_role: str = "admin"):
        super().__init(detail=f"权限不足，需要 {required_role} 角色", status_code=403)


class LLMServiceUnavailable(AppException):
    def __init__(self):
        super().__init(detail="LLM 服务暂时不可用，请稍后重试", status_code=503)


class ValidationError(AppException):
    def __init__(self, errors: list[dict]):
        self.errors = errors
        super().__init(detail="请求验证失败", status_code=422, trace_id=None)