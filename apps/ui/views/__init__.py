"""One module per workspace screen; each exposes ``render(client, project)``."""

from apps.ui.views import (
    assets,
    audit,
    film_bible,
    historical_research,
    overview,
    review,
    script_intelligence,
    storyboard,
)

# Navigation label -> view module, in sidebar order.
NAVIGATION = {
    "📽️ Project Overview": overview,
    "📄 Script Ingestion & Assets": assets,
    "⚡ Script Intelligence (G-01)": script_intelligence,
    "🏛️ Historical Research (G-02)": historical_research,
    "🎨 Storyboard Studio (G-03)": storyboard,
    "🔍 Candidate Review & Approvals": review,
    "📖 Canonical Film Bible": film_bible,
    "🛡️ Audit Trail & History": audit,
}
