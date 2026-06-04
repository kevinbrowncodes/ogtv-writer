"""Service layer.

Services hold the *business logic* and are the only place that talks to the
database for a given entity. Routes stay thin (parse input, call a service,
render a template); services stay framework-agnostic (just take a `Session`).

This separation is what makes the app testable and lets you reuse logic from a
CLI, a background job, or an API without duplicating queries.

WHERE TO ADD FEATURES: a new entity usually means a new `<entity>_service.py`
here, alongside a model, a schema, a router, and templates.
"""
