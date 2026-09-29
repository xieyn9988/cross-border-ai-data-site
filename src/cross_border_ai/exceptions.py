class CrossBorderAIError(Exception):
    """所有业务异常基类。"""


class ConfigError(CrossBorderAIError):
    """配置错误。"""


class DataValidationError(CrossBorderAIError):
    """输入数据不符合预期。"""


class BusinessLogicError(CrossBorderAIError):
    """业务计算逻辑异常。"""