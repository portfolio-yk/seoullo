from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    region: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    dataset_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    license_name: Mapped[str] = mapped_column(String(100), nullable=False)
    license_url: Mapped[str] = mapped_column(String(500), nullable=False)
    notice: Mapped[str] = mapped_column(Text, nullable=False)


class Place(Base, TimestampMixin):
    __tablename__ = "places"
    __table_args__ = (
        CheckConstraint("source IN ('dataset', 'user')", name="ck_places_source"),
        Index("ix_places_category_title", "content_type_id", "title"),
        Index("ix_places_coordinates", "latitude", "longitude"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[str | None] = mapped_column(String(50), unique=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(50), default="서울", nullable=False, index=True)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    content_type_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    address: Mapped[str] = mapped_column(String(500), default="", nullable=False, index=True)
    detail_address: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    address_source: Mapped[str] = mapped_column(String(30), default="dataset", nullable=False)
    zipcode: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    telephone: Mapped[str] = mapped_column(String(100), default="", nullable=False)

    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    map_level: Mapped[str] = mapped_column(String(10), default="", nullable=False)
    area_code: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    sigungu_code: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    legal_dong_region_code: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    legal_dong_sigungu_code: Mapped[str] = mapped_column(String(20), default="", nullable=False)

    category1: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    category2: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    category3: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    classification1: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    classification2: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    classification3: Mapped[str] = mapped_column(String(30), default="", nullable=False)

    primary_image_url: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    thumbnail_url: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    copyright_code: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    source_created_time: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    source_modified_time: Mapped[str] = mapped_column(String(20), default="", nullable=False)

    password: Mapped[str | None] = mapped_column(String(200))
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating_sum: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    images: Mapped[list[PlaceImage]] = relationship(
        back_populates="place", cascade="all, delete-orphan", order_by="PlaceImage.sort_order"
    )
    place_tags: Mapped[list[PlaceTag]] = relationship(back_populates="place", cascade="all, delete-orphan")
    reviews: Mapped[list[Review]] = relationship(back_populates="place", cascade="all, delete-orphan")
    likes: Mapped[list[PlaceLike]] = relationship(back_populates="place", cascade="all, delete-orphan")
    checkins: Mapped[list[EmotionCheckin]] = relationship(back_populates="place", cascade="all, delete-orphan")
    emotion_profile: Mapped[PlaceEmotionProfile | None] = relationship(
        back_populates="place", cascade="all, delete-orphan", uselist=False
    )


class PlaceImage(Base, TimestampMixin):
    __tablename__ = "place_images"
    __table_args__ = (
        CheckConstraint("size_bytes <= 5242880", name="ck_place_images_max_5mb"),
        UniqueConstraint("place_id", "sort_order", name="uq_place_image_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    place: Mapped[Place] = relationship(back_populates="images")


class Tag(Base, TimestampMixin):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    place_tags: Mapped[list[PlaceTag]] = relationship(back_populates="tag", cascade="all, delete-orphan")


class PlaceTag(Base):
    __tablename__ = "place_tags"

    place_id: Mapped[int] = mapped_column(ForeignKey("places.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)

    place: Mapped[Place] = relationship(back_populates="place_tags")
    tag: Mapped[Tag] = relationship(back_populates="place_tags")


class Review(Base, TimestampMixin):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating"),
        UniqueConstraint("place_id", "fingerprint_hash", name="uq_review_place_fingerprint"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id", ondelete="CASCADE"), index=True)
    fingerprint_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    password: Mapped[str] = mapped_column(String(200), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    place: Mapped[Place] = relationship(back_populates="reviews")
    likes: Mapped[list[ReviewLike]] = relationship(back_populates="review", cascade="all, delete-orphan")


class PlaceLike(Base):
    __tablename__ = "place_likes"
    __table_args__ = (UniqueConstraint("place_id", "fingerprint_hash", name="uq_place_like_fingerprint"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id", ondelete="CASCADE"), index=True)
    fingerprint_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    place: Mapped[Place] = relationship(back_populates="likes")


class ReviewLike(Base):
    __tablename__ = "review_likes"
    __table_args__ = (UniqueConstraint("review_id", "fingerprint_hash", name="uq_review_like_fingerprint"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"), index=True)
    fingerprint_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    review: Mapped[Review] = relationship(back_populates="likes")


class PlaceEmotionProfile(Base, TimestampMixin):
    __tablename__ = "place_emotion_profiles"
    __table_args__ = (
        CheckConstraint(
            "mood_fatigue >= 0 AND mood_anxiety >= 0 AND mood_stifled >= 0 "
            "AND mood_excitement >= 0 AND mood_loneliness >= 0 AND mood_calm >= 0",
            name="ck_emotion_profile_mood_nonnegative",
        ),
        CheckConstraint(
            "after_recovery >= 0 AND after_release >= 0 AND after_vitality >= 0 "
            "AND after_comfort >= 0 AND after_immersion >= 0 AND after_excitement >= 0",
            name="ck_emotion_profile_after_nonnegative",
        ),
        CheckConstraint(
            "style_quiet_solo >= 0 AND style_light_walk >= 0 "
            "AND style_new_stimulation >= 0 AND style_together >= 0",
            name="ck_emotion_profile_style_nonnegative",
        ),
    )

    place_id: Mapped[int] = mapped_column(
        ForeignKey("places.id", ondelete="CASCADE"), primary_key=True
    )
    mood_fatigue: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mood_anxiety: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mood_stifled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mood_excitement: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mood_loneliness: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mood_calm: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    after_recovery: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    after_release: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    after_vitality: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    after_comfort: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    after_immersion: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    after_excitement: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    style_quiet_solo: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    style_light_walk: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    style_new_stimulation: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    style_together: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    place: Mapped[Place] = relationship(back_populates="emotion_profile")


class EmotionCheckin(Base):
    __tablename__ = "emotion_checkins"
    __table_args__ = (
        CheckConstraint("before_intensity BETWEEN 1 AND 5", name="ck_checkin_before_intensity"),
        CheckConstraint("after_intensity BETWEEN 1 AND 5", name="ck_checkin_after_intensity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id", ondelete="CASCADE"), index=True)
    fingerprint_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    before_emotion: Mapped[str] = mapped_column(String(50), nullable=False)
    before_intensity: Mapped[int] = mapped_column(Integer, nullable=False)
    after_emotion: Mapped[str] = mapped_column(String(50), nullable=False)
    after_intensity: Mapped[int] = mapped_column(Integer, nullable=False)
    travel_style: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    place: Mapped[Place] = relationship(back_populates="checkins")
