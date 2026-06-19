"""Tests for the workflow loader."""

import uuid

import pytest
from sqlalchemy.orm import Session

from worker.engine.errors import WorkflowLoadError
from worker.engine.workflow_loader import load_workflow_version

from .conftest import simple_graph


def test_load_workflow_version(db_session: Session, make_run):
    run = make_run(simple_graph())
    version = load_workflow_version(db_session, run.workflow_version_id)
    assert version.id == run.workflow_version_id
    assert version.graph_json["nodes"]


def test_load_missing_version_raises(db_session: Session):
    with pytest.raises(WorkflowLoadError):
        load_workflow_version(db_session, uuid.uuid4())
