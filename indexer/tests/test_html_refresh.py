"""HTML cleanup and source refresh preserve policy rows and unchanged vectors."""
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from pipeline.config import get_settings
from pipeline.extract import _HTMLText
from pipeline import refresh


def test_html_removes_nested_navigation_scripts_and_footer_but_keeps_table():
    parser = _HTMLText()
    parser.feed('<head><title>Noise</title></head><nav><div>SLATE-LMS</div></nav>'
                '<script>function broken() { return 1; }</script>'
                '<main><h2>Fees</h2><table><tr><td>BS</td><td>12,000</td></tr></table></main>'
                '<footer><p>USEFUL LINKS</p></footer>')
    text = ''.join(parser.parts)
    assert 'BS | 12,000' in text
    assert 'Fees' in text
    assert all(noise not in text for noise in ['Noise', 'SLATE-LMS', 'function', 'USEFUL LINKS'])


def test_refresh_reuses_pdf_vector_and_replaces_only_requested_html(tmp_path, monkeypatch):
    html = tmp_path / 'fees.html'
    html.write_text('<nav>Noise</nav><table><tr><td>BS</td><td>12,000</td></tr></table>')
    (tmp_path / '_index.json').write_text(json.dumps([
        {'file': 'fees.html', 'doc_version': '2026', 'superseded': False}]))
    settings = replace(get_settings(), corpus_dir=str(tmp_path))
    metadata = {'source': 'rules.pdf', 'section': '4.2', 'page': 8,
                'doc_version': '2026', 'superseded': False}
    old_html = {**metadata, 'source': 'fees.html'}
    snapshot = SimpleNamespace(metadata={'embed_model': settings.embed_model}, get=lambda **kw: {
        'ids': ['pdf-unchanged', 'old-html'], 'documents': ['Original PDF policy.', 'Old fee'],
        'metadatas': [metadata, old_html], 'embeddings': [[1., 0.], [0., 1.]]})
    registry = SimpleNamespace(metadata={'active_collection': 'old-index'})
    client = SimpleNamespace(get_collection=lambda name: registry if name.endswith('-registry') else snapshot)
    monkeypatch.setattr(refresh, 'get_client', lambda s: client)
    monkeypatch.setattr(refresh, 'embed', lambda texts, s: [[.5, .5] for t in texts])
    written = []
    monkeypatch.setattr(refresh, 'store', lambda pieces, vectors, s: written.append((pieces, vectors)) or len(pieces))
    assert refresh.refresh_sources(settings, ['fees.html']) == 2
    pieces, vectors = written[0]
    assert pieces[0].id == 'pdf-unchanged' and vectors[0] == [1., 0.]
    assert pieces[1].source == 'fees.html' and pieces[1].section == 'Document'
    assert pieces[1].doc_version == '2026' and '12,000' in pieces[1].text
    assert all(p.id != 'old-html' for p in pieces)
    html.write_text('<nav>No policy here</nav>')
    with pytest.raises(ValueError, match='empty replacement'):
        refresh.refresh_sources(settings, ['fees.html'])
    assert len(written) == 1
    snapshot.metadata['embed_model'] = 'different-model'
    with pytest.raises(ValueError, match='different embedding model'):
        refresh.refresh_sources(settings, ['fees.html'])
