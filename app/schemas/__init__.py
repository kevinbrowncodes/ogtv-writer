"""Pydantic schemas package.

Schemas are the validation + serialization boundary. Models (SQLAlchemy) are the
DB shape; schemas are the request/response shape. Keeping them separate means
internal columns never leak to the UI by accident.
"""
