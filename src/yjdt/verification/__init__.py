# -*- coding: utf-8 -*-
"""
Verification - 验证模块

SIL/HIL验证框架，ODD边界验证
"""

from .sil_hil_verification import (
    # 枚举类型
    VerificationLevel,
    VerificationScope,
    TestCategory,
    TestResult,

    # 数据类
    VerificationCriteria,
    VerificationTestCase,
    VerificationResult,
    VerificationReport,

    # 验证器
    ODDBoundaryVerifier,
    SILVerificationFramework,
    HILVerificationFramework,
    IntegratedVerificationSystem,
)

__all__ = [
    "VerificationLevel",
    "VerificationScope",
    "TestCategory",
    "TestResult",
    "VerificationCriteria",
    "VerificationTestCase",
    "VerificationResult",
    "VerificationReport",
    "ODDBoundaryVerifier",
    "SILVerificationFramework",
    "HILVerificationFramework",
    "IntegratedVerificationSystem",
]
