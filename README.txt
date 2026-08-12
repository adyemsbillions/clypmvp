CLYP RECONSTRUCTION FIDELITY V2 PATCH

Replace these files in your existing Clyp Fast Dev folder:
- ai_service.py
- styles.css
- js/dashboard.js
- js/editor.js

Then stop the current server with Ctrl+C and restart:
  py start_local.py

No setup_local.py rerun is required.

Main changes:
- preserves uploaded image aspect ratio
- supports source image crop layers for photos/logos/icons/effects
- traces instead of redesigning
- keeps editable text and simple shapes
- strips large source asset before AI edit calls
