"""Experimental, in-memory scientific RAG pipeline.

PSEUDOCODE
1. Receive scientific evidence packages.
2. Validate each package through the RAG adapter.
3. Refuse the entire batch if any package fails.
4. Build an in-memory retrieval index.
5. Return citations without generating unsupported answers.

SECURITY:
This pipeline is for isolated testing only.
It does not authenticate approvals against the trusted registry.
"""

from cuselect.scientific_rag_adapter import package_to_rag_document
from cuselect.scientific_retrieval import ScientificRetriever


def build_experimental_index(packages):
    """Convert validated packages to an in-memory retriever."""

    if not isinstance(packages, list):
        raise ValueError("Expected a list of evidence packages")

    # Validate all packages before constructing the index.
    documents = [
        package_to_rag_document(package)
        for package in packages
    ]

    return ScientificRetriever(documents)


def retrieve_scientific_evidence(packages, query, top_k=3):
    """Run experimental retrieval with explicit abstention."""

    retriever = build_experimental_index(packages)

    return retriever.retrieve_with_abstention(
        query,
        top_k=top_k,
    )
