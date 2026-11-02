from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Article:
    title: str
    url: str
    summary: str
    section: str | None = None
    reading_time: str | None = None
    is_sponsor: bool = False
    source_newsletter: str | None = None
    newsletter_date: str | None = None


@dataclass
class Newsletter:
    source: str | None
    date: str | None
    view_online_url: str
    final_url: str
    articles: list[Article] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class EmailEnvelope:
    message_id: str
    from_header: str
    subject: str
    received_at: Any
    body: str


@dataclass
class SnapshotSource:
    message_id: str
    feed_name: str
    subject: str
    received_at: str
    view_online_url: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DeliveryStatus:
    state: str = "pending"
    attempted_at: str | None = None
    detail: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "DeliveryStatus":
        data = data or {}
        return cls(
            state=data.get("state", "pending"),
            attempted_at=data.get("attempted_at"),
            detail=data.get("detail"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunManifest:
    target_date: str
    cutoff_at: str
    allowed_feeds: list[str]
    source_messages: list[dict[str, Any]] = field(default_factory=list)
    snapshot_status: str = "pending"
    digest_status: str = "pending"
    email: DeliveryStatus = field(default_factory=DeliveryStatus)
    telegram: DeliveryStatus = field(default_factory=DeliveryStatus)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunManifest":
        return cls(
            target_date=data["target_date"],
            cutoff_at=data["cutoff_at"],
            allowed_feeds=list(data.get("allowed_feeds", [])),
            source_messages=list(data.get("source_messages", [])),
            snapshot_status=data.get("snapshot_status", "pending"),
            digest_status=data.get("digest_status", "pending"),
            email=DeliveryStatus.from_dict(data.get("email")),
            telegram=DeliveryStatus.from_dict(data.get("telegram")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_date": self.target_date,
            "cutoff_at": self.cutoff_at,
            "allowed_feeds": self.allowed_feeds,
            "source_messages": self.source_messages,
            "snapshot_status": self.snapshot_status,
            "digest_status": self.digest_status,
            "email": self.email.to_dict(),
            "telegram": self.telegram.to_dict(),
        }


@dataclass
class DigestArticle:
    title: str
    source_newsletter: str
    url: str
    tldr_summary: str
    why_important: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DigestArticle":
        return cls(
            title=data["title"],
            source_newsletter=data["source_newsletter"],
            url=data["url"],
            tldr_summary=data["tldr_summary"],
            why_important=data.get("why_important"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DigestArtifact:
    target_date: str
    source_newsletters: list[str]
    executive_summary: str
    principal_articles: list[DigestArticle]
    secondary_articles: list[DigestArticle]
    extraction_notes: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DigestArtifact":
        return cls(
            target_date=data["target_date"],
            source_newsletters=list(data.get("source_newsletters", [])),
            executive_summary=data["executive_summary"],
            principal_articles=[DigestArticle.from_dict(item) for item in data.get("principal_articles", [])],
            secondary_articles=[DigestArticle.from_dict(item) for item in data.get("secondary_articles", [])],
            extraction_notes=list(data.get("extraction_notes", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_date": self.target_date,
            "source_newsletters": self.source_newsletters,
            "executive_summary": self.executive_summary,
            "principal_articles": [article.to_dict() for article in self.principal_articles],
            "secondary_articles": [article.to_dict() for article in self.secondary_articles],
            "extraction_notes": self.extraction_notes,
        }
