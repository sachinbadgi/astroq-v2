"""
Phase 5 Tests: ChartDNA Persistence (AutoResearch 2.0)

Tests for: ChartDNARepository.save, load, list_all, upsert.
"""

import os
import sqlite3
import pytest
from astroq.lk_prediction.lse_chart_dna import ChartDNARepository
from astroq.lk_prediction.data_contracts import ChartDNA


@pytest.fixture
def repo(tmp_path):
    db_path = str(tmp_path / "test_dna.db")
    return ChartDNARepository(db_path)


def _make_dna(fig_id: str = "test_fig") -> ChartDNA:
    return ChartDNA(
        figure_id=fig_id,
        back_test_hit_rate=0.8,
        mean_offset_years=1.2,
        iterations_run=5,
        delay_constants={"delay.sun_h1": 2.0},
        grammar_overrides={"grammar.h10_sleep": True},
        config_overrides={"delay.sun_h1": 2.0, "grammar.h10_sleep": True},
        confidence_score=0.75
    )


# --------------------------------------------------------------------------
# Test 1: Save and Load Round-trip
# --------------------------------------------------------------------------

def test_repo_save_load(repo):
    dna = _make_dna("f1")
    repo.save(dna)
    
    loaded = repo.load("f1")
    assert loaded is not None
    assert loaded.figure_id == "f1"
    assert loaded.back_test_hit_rate == 0.8
    assert loaded.delay_constants == {"delay.sun_h1": 2.0}
    assert loaded.grammar_overrides == {"grammar.h10_sleep": True}
    assert loaded.confidence_score == 0.75


# --------------------------------------------------------------------------
# Test 2: Upsert (Overwrite existing)
# --------------------------------------------------------------------------

def test_repo_upsert(repo):
    dna1 = _make_dna("f1")
    repo.save(dna1)
    
    dna2 = _make_dna("f1")
    dna2.back_test_hit_rate = 1.0
    repo.save(dna2)
    
    loaded = repo.load("f1")
    assert loaded.back_test_hit_rate == 1.0


# --------------------------------------------------------------------------
# Test 3: Load missing returns None
# --------------------------------------------------------------------------

def test_repo_load_missing(repo):
    assert repo.load("nonexistent") is None


# --------------------------------------------------------------------------
# Test 4: List All
# --------------------------------------------------------------------------

def test_repo_list_all(repo):
    repo.save(_make_dna("f1"))
    repo.save(_make_dna("f2"))
    
    all_dna = repo.list_all()
    assert len(all_dna) == 2
    ids = [d.figure_id for d in all_dna]
    assert "f1" in ids
    assert "f2" in ids


# --------------------------------------------------------------------------
# Test 5: Table initialization
# --------------------------------------------------------------------------

def test_repo_init_table(tmp_path):
    db_path = str(tmp_path / "init_test.db")
    # Just instantiating should create the table
    repo = ChartDNARepository(db_path)
    
    con = sqlite3.connect(db_path)
    cur = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chart_dna'")
    assert cur.fetchone() is not None
    con.close()
