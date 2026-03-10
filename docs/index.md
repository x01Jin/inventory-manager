# Inventory Manager Documentation

This project is a desktop app for laboratory inventory and requisition tracking.
These docs are written to be understandable for:

- Non-technical stakeholders who want to understand what the system does
- Junior developers who need to work in the codebase safely
- Maintainers who need clear limits and risks before making changes

## Start Here

If this is your first time in the project, read in this order:

1. [Installation](installation.md)
2. [User Guide](usage.md)
3. [System Overview](architecture.md)
4. [Services](api.md)
5. [Development](development.md)

## One-Page Summary

- The app is a PyQt6 desktop application.
- Data is stored in a local SQLite database (`inventory.db`).
- Core business logic is in `inventory_app/services`.
- UI pages live in `inventory_app/gui`.
- Database schema is in `inventory_app/database/schema.sql`.

## Detailed Feature Docs

If you want feature-by-feature pages, these are still available:

- [Dashboard](dashboard.md)
- [Inventory](inventory.md)
- [Requisitions](requisitions.md)
- [Requesters](requesters.md)
- [Reports](reports.md)
- [Settings](settings.md)
- [General Help](help-general.md)

## View Docs Locally

```powershell
pip install mkdocs mkdocs-material
mkdocs serve
```

Then open `http://127.0.0.1:8000`.
