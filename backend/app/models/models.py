import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class CharacterRole(str, PyEnum):
    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    SUPPORTING = "supporting"
    MINOR = "minor"


class Novel(Base):
    __tablename__ = "novels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    genre: Mapped[str] = mapped_column(String(200), default="")
    style_notes: Mapped[str] = mapped_column(Text, default="")
    word_count_goal: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    characters: Mapped[list["Character"]] = relationship("Character", back_populates="novel", cascade="all, delete-orphan")
    settings: Mapped[list["Setting"]] = relationship("Setting", back_populates="novel", cascade="all, delete-orphan")
    outline_nodes: Mapped[list["OutlineNode"]] = relationship("OutlineNode", back_populates="novel",
                                                                cascade="all, delete-orphan")


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    novel_id: Mapped[int] = mapped_column(ForeignKey("novels.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    role: Mapped[CharacterRole] = mapped_column(Enum(CharacterRole), default=CharacterRole.SUPPORTING)
    profile: Mapped[dict] = mapped_column(JSON, default=dict)
    arc: Mapped[str] = mapped_column(Text, default="")
    avatar_color: Mapped[str] = mapped_column(String(20), default="#6366f1")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    novel: Mapped["Novel"] = relationship("Novel", back_populates="characters")
    relationships_as_source: Mapped[list["CharacterRelationship"]] = relationship(
        "CharacterRelationship", foreign_keys="CharacterRelationship.source_id",
        cascade="all, delete-orphan", back_populates="source"
    )
    relationships_as_target: Mapped[list["CharacterRelationship"]] = relationship(
        "CharacterRelationship", foreign_keys="CharacterRelationship.target_id",
        cascade="all, delete-orphan", back_populates="target"
    )


class CharacterRelationship(Base):
    __tablename__ = "character_relationships"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), nullable=False)
    target_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")

    source: Mapped["Character"] = relationship("Character", foreign_keys=[source_id], back_populates="relationships_as_source")
    target: Mapped["Character"] = relationship("Character", foreign_keys=[target_id], back_populates="relationships_as_target")


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    novel_id: Mapped[int] = mapped_column(ForeignKey("novels.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="location")
    location_type: Mapped[str] = mapped_column(String(100), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    notable_features: Mapped[list] = mapped_column(JSON, default=list)
    chapters_featured: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    novel: Mapped["Novel"] = relationship("Novel", back_populates="settings")


class OutlineNode(Base):
    __tablename__ = "outline_nodes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    novel_id: Mapped[int] = mapped_column(ForeignKey("novels.id"), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("outline_nodes.id"), nullable=True)
    node_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50), default="planned")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text, default="")
    chapter_prompt: Mapped[str] = mapped_column(Text, default="")
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    novel: Mapped["Novel"] = relationship("Novel", back_populates="outline_nodes")
    children: Mapped[list["OutlineNode"]] = relationship("OutlineNode", back_populates="parent",
                                                          foreign_keys=[parent_id],
                                                          cascade="all, delete-orphan",
                                                          order_by="OutlineNode.sort_order")
    parent: Mapped["OutlineNode | None"] = relationship("OutlineNode", back_populates="children",
                                                          foreign_keys=[parent_id], remote_side=[id])
