#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: facesdk/sdk/python/facesdk/models.py
Copyright (c) 2024 FaceSDK Contributors
MIT License

FaceSDK Python SDK - Data Models
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class BoundingBox:
    """人脸边界框"""
    x_min: int
    y_min: int
    x_max: int
    y_max: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BoundingBox":
        return cls(
            x_min=data.get("x_min", 0),
            y_min=data.get("y_min", 0),
            x_max=data.get("x_max", 0),
            y_max=data.get("y_max", 0),
        )

    def __repr__(self) -> str:
        return f"BoundingBox(x={self.x_min}, y={self.y_min}, w={self.x_max - self.x_min}, h={self.y_max - self.y_min})"


@dataclass
class Quality:
    """人脸质量评分"""
    score: float = 0.0
    brightness: float = 0.0
    sharpness: float = 0.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Quality":
        return cls(
            score=data.get("score", 0.0),
            brightness=data.get("brightness", 0.0),
            sharpness=data.get("sharpness", 0.0),
        )


@dataclass
class Face:
    """人脸检测结果"""
    bounding_box: BoundingBox
    landmarks: List[List[int]] = field(default_factory=list)
    confidence: float = 0.0
    quality: Optional[Quality] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Face":
        return cls(
            bounding_box=BoundingBox.from_dict(data.get("box", {})),
            landmarks=data.get("landmarks", []),
            confidence=data.get("confidence", 0.0),
            quality=Quality.from_dict(data.get("quality", {})) if "quality" in data else None,
        )


@dataclass
class FaceRecord:
    """人脸记录"""
    image_id: str
    subject_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FaceRecord":
        return cls(
            image_id=data.get("image_id", ""),
            subject_id=data.get("subject", ""),
            created_at=_parse_datetime(data.get("created_at")),
            updated_at=_parse_datetime(data.get("updated_at")),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Subject:
    """人脸库（Subject）"""
    subject_id: str
    name: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    faces: List[FaceRecord] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Subject":
        return cls(
            subject_id=data.get("subject", ""),
            name=data.get("name", ""),
            created_at=_parse_datetime(data.get("created_at")),
            updated_at=_parse_datetime(data.get("updated_at")),
            faces=[FaceRecord.from_dict(f) for f in data.get("faces", [])],
        )


@dataclass
class DetectionResult:
    """人脸检测结果"""
    faces: List[Face]
    image_id: str = ""
    face_count: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DetectionResult":
        return cls(
            faces=[Face.from_dict(f) for f in data.get("faces", [])],
            image_id=data.get("image_id", ""),
            face_count=data.get("face_count", 0),
        )


@dataclass
class CompareResult:
    """人脸比对结果"""
    similarity: float = 0.0
    distance: float = 0.0
    threshold: float = 0.0
    match: bool = False
    face1: Optional[Face] = None
    face2: Optional[Face] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompareResult":
        return cls(
            similarity=data.get("similarity", 0.0),
            distance=data.get("distance", 0.0),
            threshold=data.get("threshold", 0.0),
            match=data.get("is_match", False),
            face1=Face.from_dict(data.get("face1", {})) if "face1" in data else None,
            face2=Face.from_dict(data.get("face2", {})) if "face2" in data else None,
        )


@dataclass
class MatchResult:
    """搜索匹配结果"""
    subject_id: str = ""
    similarity: float = 0.0
    distance: float = 0.0
    match: bool = False
    face: Optional[Face] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MatchResult":
        return cls(
            subject_id=data.get("subject", ""),
            similarity=data.get("similarity", 0.0),
            distance=data.get("distance", 0.0),
            match=data.get("is_match", False),
            face=Face.from_dict(data.get("face", {})) if "face" in data else None,
        )


@dataclass
class SearchResult:
    """人脸识别（1:N 搜索）结果"""
    results: List[MatchResult]
    face_count: int = 0
    image_id: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchResult":
        return cls(
            results=[MatchResult.from_dict(r) for r in data.get("results", [])],
            face_count=data.get("face_count", 0),
            image_id=data.get("image_id", ""),
        )


def _parse_datetime(value: Any) -> Optional[datetime]:
    """解析日期时间字符串"""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        # ISO 8601 格式
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
