"""Phase B product navigation without changing the legacy Journey surfaces."""
import re

from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def primary_navigation(page: str) -> str:
    return page.split('<nav class="product-nav" aria-label="Primary navigation">', 1)[1].split('</nav>', 1)[0]


def test_reports_and_collections_routes_use_two_destination_mrj_shell():
    for route, selected in (("/reports", "Reports"), ("/collections", "Collections")):
        response = client.get(route)
        assert response.status_code == 200
        page = response.text
        assert 'data-product-brand="mrj"' in page
        assert 'class="product-skip-link" href="#main"' in page
        assert '<main id="main"' in page
        assert '/assets/brand/mrj/icon_only/png/MRJ_icon_128.png' in page
        navigation = primary_navigation(page)
        assert re.findall(r'<a[^>]+>(Reports|Collections)</a>', navigation) == ["Reports", "Collections"]
        assert navigation.count('aria-current="page"') == 1
        assert f'href="{route}" aria-current="page">{selected}</a>' in navigation
        assert not any(stage in navigation for stage in (
            "UNDERSTAND", "PROTECT", "EXTRACT", "STANDARDIZE", "ANALYZE", "VISUALIZE", "INDICATORS"))


def test_reports_shell_preserves_functional_single_and_batch_entry():
    page = client.get("/reports").text
    assert '<h1 id="page-title">Reports</h1>' in page
    assert 'id="add-reports" type="button">Add reports' in page
    assert 'id="report-files"' in page and 'multiple aria-label="Choose reports to upload"' in page
    assert 'id="report-queue-list"' in page and 'id="clinical-record"' in page
    assert 'src="/static/reports.js?v=c2c"' in page
    assert '/understanding' not in page
    assert client.get("/understanding").status_code == 200
    assert client.get("/privacy").status_code == 200


def test_collections_shell_reuses_existing_governed_collection_api():
    page = client.get("/collections").text
    script = client.get("/static/collections.js")
    styles = client.get("/static/product-shell.css")
    assert script.status_code == styles.status_code == 200
    assert '<h1 id="page-title">Collections</h1>' in page
    assert 'id="collection-list"' in page and 'id="collection-detail"' in page
    assert "'/api/v1/understanding/analysis-collections'" in script.text
    assert "collection.name" in script.text and "textContent" in script.text
    assert "innerHTML" not in script.text
    assert client.get("/api/v1/understanding/analysis-collections").status_code == 200
    assert "@media (max-width: 800px)" in styles.text
    assert "@media (max-width: 520px)" in styles.text


def test_landing_workspace_entry_goes_to_reports_without_changing_hero():
    page = client.get("/app").text
    assert 'class="landing-button header-cta" href="/reports"' in page
    assert 'class="landing-button button-paper" href="/reports">Open Reports' in page
    assert 'class="text-link" href="/reports">Explore Radiology' in page
    assert "Every Medical Report" in page and "Has a Journey." in page
    assert "/assets/video/mrj-kling-cinematic.mp4" in page
    assert 'href="/understanding"' in page  # Legacy stage link remains available.


def test_legacy_stage_endpoints_and_routes_remain_registered():
    paths = app.openapi()["paths"]
    for route in ("/understanding", "/privacy", "/api/v1/understanding/journey-runs",
                  "/api/v1/understanding/analysis-collections",
                  "/api/v1/understanding/journey-runs/{run_id}/protect",
                  "/api/v1/understanding/journey-runs/{run_id}/documents/{document_id}/extract",
                  "/api/v1/understanding/journey-runs/{run_id}/documents/{document_id}/standardize",
                  "/api/v1/understanding/analysis-collections/{collection_id}/analyze",
                  "/api/v1/understanding/analysis-runs/{analysis_run_id}/visualize",
                  "/api/v1/understanding/analysis-runs/{analysis_run_id}/indicators"):
        assert route in paths
