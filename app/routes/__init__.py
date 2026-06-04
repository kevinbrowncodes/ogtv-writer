"""HTTP routers.

Each module here owns one feature area and exposes a `router` (APIRouter).
Routers are mounted in `app.main._register_routers`.

NAMING CONVENTIONS (keep these consistent across the app):
  - Module:        app/routes/<feature>.py          e.g. items.py
  - Page routes:   GET  /<feature>                   -> pages/<feature>.html
  - HTMX partials: GET  /<feature>/<verb>            -> partials/<feature>/_*.html
  - Mutations:     POST/PUT/DELETE /<feature>/{id}
  - Route fn name: <feature>_<action>                e.g. items_create
"""
