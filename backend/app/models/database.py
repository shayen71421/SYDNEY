from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, JSON, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func
import enum

from app.core.config import settings


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.debug,
)


class Base(DeclarativeBase):
    pass


class Gene(Base):
    __tablename__ = "genes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    chromosome = Column(String(10))
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    variants = relationship("Variant", back_populates="gene")
    papers = relationship("Paper", secondary="gene_papers", back_populates="genes")


class Variant(Base):
    __tablename__ = "variants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    gene_id = Column(Integer, ForeignKey("genes.id"), nullable=False)
    hgvs_c = Column(String(255), index=True)
    hgvs_p = Column(String(255), index=True)
    protein_change = Column(String(255))
    variant_type = Column(String(50))
    description = Column(Text)
    clinical_significance = Column(String(100))
    clinvar_id = Column(String(50))
    clinvar_data = Column(JSON)
    review_status = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    gene = relationship("Gene", back_populates="variants")
    evidence = relationship("Evidence", back_populates="variant")
    reports = relationship("Report", back_populates="variant")
    why_matters = Column(Text)


class Disease(Base):
    __tablename__ = "diseases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    mondo_id = Column(String(50))
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    papers = relationship("Paper", secondary="disease_papers", back_populates="diseases")


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pmid = Column(String(20), unique=True, index=True)
    title = Column(String(500))
    authors = Column(Text)
    journal = Column(String(255))
    year = Column(Integer)
    abstract = Column(Text)
    doi = Column(String(255))
    study_type = Column(String(100))
    keywords = Column(JSON)
    embedding = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    genes = relationship("Gene", secondary="gene_papers", back_populates="papers")
    diseases = relationship("Disease", secondary="disease_papers", back_populates="papers")
    evidence = relationship("Evidence", back_populates="paper")


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    variant_id = Column(Integer, ForeignKey("variants.id"), nullable=False)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    evidence_type = Column(String(100))
    relevance_score = Column(Float, default=0.0)
    study_quality_score = Column(Float, default=0.0)
    recency_score = Column(Float, default=0.0)
    evidence_score = Column(Float, default=0.0)
    key_findings = Column(Text)
    source = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    variant = relationship("Variant", back_populates="evidence")
    paper = relationship("Paper", back_populates="evidence")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    variant_id = Column(Integer, ForeignKey("variants.id"), nullable=False)
    confidence_level = Column(String(50))
    confidence_score = Column(Float)
    evidence_volume = Column(Integer)
    evidence_quality = Column(Float)
    study_agreement = Column(Float)
    executive_summary = Column(Text)
    clinical_significance = Column(Text)
    disease_associations = Column(JSON)
    mechanism_of_action = Column(Text)
    evidence_overview = Column(Text)
    clinvar_review_strength = Column(Float, default=0.0)
    confidence_assessment = Column(Text)
    research_gaps = Column(JSON)
    ai_summary = Column(Text)
    report_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    variant = relationship("Variant", back_populates="reports")


class GenePaper(Base):
    __tablename__ = "gene_papers"

    gene_id = Column(Integer, ForeignKey("genes.id"), primary_key=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), primary_key=True)


class DiseasePaper(Base):
    __tablename__ = "disease_papers"

    disease_id = Column(Integer, ForeignKey("diseases.id"), primary_key=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), primary_key=True)
